"""Windows stand-in for the `rubberband` CLI, backed by ffmpeg's rubberband filter.

The Genjustsu pipeline calls: rubberband --fine --pitch <semitones> --time 1 in.wav out.wav
ffmpeg's rubberband filter gives the same pitch shift with timing preserved.
"""
import subprocess
import sys

import imageio_ffmpeg


def main():
    args = sys.argv[1:]
    pitch = 0.0
    files = []
    i = 0
    while i < len(args):
        if args[i] == '--pitch':
            pitch = float(args[i + 1]); i += 2
        elif args[i] == '--time':
            i += 2
        elif args[i] == '--fine':
            i += 1
        else:
            files.append(args[i]); i += 1
    if len(files) != 2:
        raise SystemExit('usage: rubberband [--fine] --pitch N --time 1 in.wav out.wav')
    src, dst = files
    ratio = 2 ** (pitch / 12.0)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, '-y', '-i', src, '-af', 'rubberband=pitch=%f' % ratio,
                    '-c:a', 'pcm_s16le', dst], check=True)


if __name__ == '__main__':
    main()
