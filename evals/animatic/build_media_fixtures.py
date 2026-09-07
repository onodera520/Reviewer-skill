"""Build synthetic media only; never modifies user videos. Requires local FFmpeg."""
import json
from pathlib import Path
import subprocess
import sys


def build(directory, ffmpeg):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    def encode(name, args):
        target = directory / name
        subprocess.run([ffmpeg, '-hide_banner', '-nostdin', '-v', 'error', '-y', *args, str(target)], check=True)
        return target
    hard = encode('hard-cut.mkv', ['-f', 'lavfi', '-i', 'color=black:s=160x120:r=10:d=0.5',
        '-f', 'lavfi', '-i', 'color=white:s=160x120:r=10:d=0.1',
        '-f', 'lavfi', '-i', 'color=blue:s=160x120:r=10:d=0.5',
        '-filter_complex', '[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]', '-map', '[v]', '-c:v', 'ffv1'])
    encode('silent.mkv', ['-i', str(hard), '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono',
        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'pcm_s16le', '-shortest'])
    encode('tone.mkv', ['-i', str(hard), '-f', 'lavfi', '-i', 'sine=frequency=800:sample_rate=16000',
        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'pcm_s16le', '-shortest'])
    encode('fade.mkv', ['-f', 'lavfi', '-i', 'color=white:s=160x120:r=10:d=1.1',
        '-vf', 'fade=t=in:st=0:d=0.5', '-c:v', 'ffv1'])
    encode('vfr.mkv', ['-f', 'lavfi', '-i', 'testsrc2=s=160x120:r=10:d=1.5',
        '-vf', "select='eq(n,0)+eq(n,1)+eq(n,4)+eq(n,9)+eq(n,14)'",
        '-fps_mode', 'vfr', '-c:v', 'ffv1'])
    (directory / 'damaged.mkv').write_bytes(b'not a valid media file')
    truth = {'hard-cut.mkv': {'cuts_seconds': [0.5, 0.6], 'audio': 'none'},
             'silent.mkv': {'audio': 'digital_silence'}, 'tone.mkv': {'audio': 'synthetic_tone_not_classified_as_music'},
             'fade.mkv': {'transition': 'fade_in'}, 'vfr.mkv': {'frame_pts_seconds': [0, 0.1, 0.4, 0.9, 1.4]},
             'damaged.mkv': {'decode': 'failure'}}
    (directory / 'media-truth.json').write_text(json.dumps(truth, indent=2), encoding='utf-8')
    return truth


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
