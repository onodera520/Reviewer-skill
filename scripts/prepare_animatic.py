#!/usr/bin/env python3
"""Prepare local media evidence. This script NEVER performs a semantic review.

FFmpeg/FFprobe: --ffmpeg/--ffprobe, REVIEWER_FFMPEG/REVIEWER_FFPROBE,
then scripts/media-tools.local.json, then PATH. Output must be a new directory.
Original media is never modified. The optional local config is not portable.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


class MediaError(ValueError):
    pass


def executable(name, explicit=None):
    candidate = explicit or os.environ.get('REVIEWER_' + name.upper())
    config_path = Path(__file__).with_name('media-tools.local.json')
    if not candidate and config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding='utf-8-sig'))
            candidate = config.get(name)
        except (OSError, ValueError, AttributeError) as exc:
            raise MediaError(f'Invalid local media configuration: {config_path}') from exc
    candidate = candidate or shutil.which(name)
    if not candidate or not Path(candidate).is_file():
        raise MediaError(f'{name} unavailable: use --{name} PATH or REVIEWER_{name.upper()}; install a trusted local build.')
    return str(Path(candidate).resolve())


def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
    if result.returncode:
        raise MediaError(f'{Path(args[0]).name} failed: {result.stderr[-3000:]}')
    return result


def probe_video(path, ffprobe):
    data = json.loads(run([ffprobe, '-v', 'error', '-select_streams', 'v:0',
        '-show_frames', '-show_streams', '-show_format', '-show_entries',
        'frame=best_effort_timestamp_time,pkt_duration_time,duration_time:stream:format',
        '-of', 'json', path]).stdout)
    if not data.get('streams') or not data.get('frames'):
        raise MediaError('No decodable video frames.')
    frames = []
    for index, item in enumerate(data['frames']):
        try:
            pts = float(item['best_effort_timestamp_time'])
        except (KeyError, ValueError):
            raise MediaError('A decoded frame has no usable presentation timestamp.')
        if not math.isfinite(pts) or (frames and pts <= frames[-1]['source_pts_seconds']):
            raise MediaError('Non-finite or non-increasing frame timestamps; timing requires manual verification.')
        frames.append({'frame_index': index, 'source_pts_seconds': pts,
                       'duration_seconds': float(item.get('duration_time', item.get('pkt_duration_time', 0)) or 0)})
    origin = frames[0]['source_pts_seconds']
    for frame in frames:
        frame['time_seconds'] = round(frame['source_pts_seconds'] - origin, 9)
    # No assumed frame rate, including VFR. Last duration comes from the decoder.
    end = frames[-1]['time_seconds'] + frames[-1]['duration_seconds']
    if end <= frames[-1]['time_seconds']:
        raise MediaError('Final frame duration unavailable; cannot establish full decoded range.')
    return data, frames, origin, end


def sample_indices(frames, boundaries, samples=3, anchor_times=(), dense_ranges=()):
    chosen = set()
    count = len(frames)
    for start, stop in zip(boundaries, boundaries[1:]):
        if stop <= start:
            continue
        chosen.update((start, stop - 1))
        # Time-based selection retains endpoints even for one-frame shots.
        lo, hi = frames[start]['time_seconds'], frames[stop - 1]['time_seconds']
        for n in range(samples):
            target = lo + (hi - lo) * n / max(1, samples - 1)
            chosen.add(min(range(start, stop), key=lambda i: abs(frames[i]['time_seconds'] - target)))
    for cut in boundaries[1:-1]:
        chosen.update(i for i in (cut - 1, cut) if 0 <= i < count)
    for target in anchor_times:
        chosen.add(min(range(count), key=lambda i: abs(frames[i]['time_seconds'] - target)))
    for span in dense_ranges:
        chosen.update(i for i, frame in enumerate(frames)
                      if span['start_seconds'] <= frame['time_seconds'] <= span['end_seconds'])
    return sorted(chosen)


def prepare(video, output, *, ffmpeg=None, ffprobe=None, threshold=0.12,
            samples=3, provided_segments=(), anchor_times=(), dense_ranges=()):
    ffmpeg, ffprobe = executable('ffmpeg', ffmpeg), executable('ffprobe', ffprobe)
    video, output = Path(video).resolve(), Path(output).resolve()
    if not video.is_file():
        raise MediaError('Video reference is not a readable local file.')
    if output.exists():
        raise MediaError('Output directory already exists; use a new directory to preserve evidence.')
    if not 0 < threshold < 1 or samples < 2:
        raise MediaError('threshold must be between 0 and 1; samples must be at least 2.')
    metadata, frames, origin, duration = probe_video(video, ffprobe)
    for span in [*provided_segments, *dense_ranges]:
        if not 0 <= span['start_seconds'] < span['end_seconds'] <= duration + 0.001:
            raise MediaError('A requested segment is outside the decoded timeline.')
    if any(not 0 <= t <= duration for t in anchor_times):
        raise MediaError('Anchor time is outside the decoded timeline.')
    output.mkdir(parents=True)
    limitations = ['Extraction is not inspection. Shot matching, story intent and transitions require visual review.',
                   'Scene-change scores are candidates, not confirmed hard cuts; slow transitions and similar shots can evade detection.']
    # Full decode; showinfo PTS retain input origin through -copyts.
    scan = run([ffmpeg, '-hide_banner', '-nostdin', '-v', 'info', '-xerror', '-copyts',
                '-i', video, '-map', '0:v:0', '-an', '-vf',
                f"select='gt(scene,{threshold})',showinfo", '-fps_mode', 'passthrough', '-f', 'null', '-'])
    candidate_pts = [float(x) for x in re.findall(r'pts_time:([\d.eE+\-]+)', scan.stderr)]
    cuts = sorted({min(range(len(frames)), key=lambda i: abs(frames[i]['source_pts_seconds'] - pts))
                   for pts in candidate_pts} - {0})
    boundaries = sorted({0, len(frames), *cuts})
    # User hints add sampling boundaries; they never become verified mappings/cuts.
    hint_indices = {min(range(len(frames)), key=lambda i: abs(frames[i]['time_seconds'] - s['start_seconds']))
                    for s in provided_segments}
    hint_indices.update(min(range(len(frames)), key=lambda i: abs(frames[i]['time_seconds'] - s['end_seconds']))
                        for s in provided_segments if s['end_seconds'] < duration)
    sample_boundaries = sorted(set(boundaries) | hint_indices)
    selected = sample_indices(frames, sample_boundaries, samples, anchor_times, dense_ranges)
    # Bounded batches avoid Windows command length limits. Decode by frame index, never index/fps.
    exported = []
    for batch_start in range(0, len(selected), 200):
        batch = selected[batch_start:batch_start + 200]
        expression = '+'.join(f'eq(n,{i})' for i in batch)
        pattern = output / f'batch-{batch_start:06d}-%06d.png'
        run([ffmpeg, '-hide_banner', '-nostdin', '-v', 'error', '-xerror', '-i', video,
             '-map', '0:v:0', '-an', '-vf', f"select='{expression}'", '-fps_mode', 'passthrough', pattern])
        files = sorted(output.glob(f'batch-{batch_start:06d}-*.png'))
        if len(files) != len(batch):
            raise MediaError('Exported frame count differs from decoded selection; evidence incomplete.')
        for index, file in zip(batch, files):
            target = output / f'frame-{index:08d}.png'
            file.rename(target)
            exported.append({**frames[index], 'ref': str(target), 'inspected': False})
    streams = json.loads(run([ffprobe, '-v', 'error', '-show_streams', '-of', 'json', video]).stdout)['streams']
    # Audio stream metadata is not a content check. Never extract/decode audio or run OCR.
    manifest = {'schema_version': '1.0', 'review_mode': 'animatic', 'review_profile':'story_preview', 'preparation_only': True,
        'video_ref': str(video), 'duration_seconds': duration, 'timestamp_origin_seconds': origin,
        'timestamp_convention': 'time_seconds = decoded PTS minus first video PTS; source PTS retained',
        'streams': streams, 'frames': frames, 'extracted_frames': exported,
        'cut_candidates': [{'time_seconds': frames[i]['time_seconds'], 'frame_index': i,
                            'previous_frame_index': i - 1, 'verified': False} for i in cuts],
        'provided_segments': list(provided_segments), 'provided_segments_verified': False,
        'candidate_segments': [{'start_seconds': frames[a]['time_seconds'],
             'end_seconds': frames[b]['time_seconds'] if b < len(frames) else duration,
             'shot_id': None, 'mapping_status': 'uncertain'} for a, b in zip(boundaries, boundaries[1:])],
        'audio': {'status':'not_applicable','method':'skipped_by_scope','checked_ranges':[],'evidence':[]},
        'coverage': {'decoded_ranges': [{'start_seconds': 0, 'end_seconds': duration}],
                     'decode_completed': True, 'reviewed_shot_ids': [], 'visual_inspection_completed': False,
                     'limitations': limitations}}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video')
    parser.add_argument('--output', required=True)
    parser.add_argument('--ffmpeg')
    parser.add_argument('--ffprobe')
    parser.add_argument('--threshold', type=float, default=0.12)
    parser.add_argument('--samples', type=int, default=3)
    parser.add_argument('--segments', help='JSON list: shot_id, start_seconds, end_seconds; unverified hints')
    parser.add_argument('--anchor-time', type=float, action='append', default=[])
    parser.add_argument('--dense-ranges', help='JSON list of start_seconds/end_seconds; exports every decoded frame within ranges')
    args = parser.parse_args()
    try:
        segments = json.loads(Path(args.segments).read_text(encoding='utf-8')) if args.segments else []
        dense = json.loads(Path(args.dense_ranges).read_text(encoding='utf-8')) if args.dense_ranges else []
        prepare(args.video, args.output, ffmpeg=args.ffmpeg, ffprobe=args.ffprobe, threshold=args.threshold,
                samples=args.samples, provided_segments=segments, anchor_times=args.anchor_time, dense_ranges=dense)
    except (MediaError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Preparation incomplete: {exc}', file=sys.stderr)
        return 2
    print(str(Path(args.output).resolve() / 'manifest.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
