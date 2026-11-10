#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 AmigaNarrator contributors
# SPDX-License-Identifier: 0BSD
"""Synthesize English text or narrator phonemes, then play or save the audio."""

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import wave


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="text to speak (end sentences with a period)")
    parser.add_argument("accent", nargs="?", help="translator42 accent (requires its library and files)")
    parser.add_argument("--phonetic", action="store_true", help="treat text as narrator phonemes and skip translation")
    parser.add_argument("-o", "--output", metavar="FILE.wav", help="save a WAV file instead of playing audio (no player required)")
    parser.add_argument("-r", "--rate", type=int, default=150, help="words per minute: 40-400 (default: 150)")
    parser.add_argument("-p", "--pitch", type=int, default=110, help="pitch: 65-320 (default: 110)")
    parser.add_argument("-m", "--mode", type=int, choices=(0, 1), default=0, help="0=natural, 1=robotic")
    parser.add_argument("-s", "--sex", type=int, choices=(0, 1), default=0, help="0=male, 1=female")
    parser.add_argument("-f", "--frequency", type=int, default=22200, help="sample rate: 5000-28000 Hz (default: 22200)")
    parser.add_argument("-d", "--device", default=os.environ.get("DEV_PATH", "./Devs/narrator.device"), help="narrator.device path (or DEV_PATH)")
    args = parser.parse_args()
    if args.phonetic and args.accent is not None:
        parser.error("--phonetic cannot be combined with an accent")
    for name, low, high in (("rate", 40, 400), ("pitch", 65, 320), ("frequency", 5000, 28000)):
        if not low <= getattr(args, name) <= high:
            parser.error(f"--{name} must be between {low} and {high}")

    def binary(name):
        return str(Path(os.environ.get("OUTDIR", "./bin")).resolve() / (name + os.environ.get("EXE", "")))

    library = os.environ.get("LIB_PATH") or (
        "./Libs/v33_translator.library" if args.accent else "./Libs/translator.library"
    )
    required = [args.device]
    if not args.phonetic:
        required.append(library)
    if not args.phonetic and args.accent:
        accents = os.environ.get("ACCENT_DIR", "./Accents")
        required.append(str(Path(accents) / (args.accent + ".accent")))
        translator = [binary("translateas"), "-d", accents + "/", "-l", library, "-q", "--", args.accent, args.text]
    elif not args.phonetic:
        translator = [binary("translator"), "-l", library, args.text]
    for filename in required:
        if not Path(filename).is_file():
            parser.error(f"required runtime file missing: {filename}")

    if args.output is None:
        # PLAYSTDIN is an argument list, never a shell command.
        if os.environ.get("PLAYSTDIN"):
            player = shlex.split(os.environ["PLAYSTDIN"])
        else:
            player_name = shutil.which("play_ng") or shutil.which("play")
            if not player_name:
                parser.error("install the sox package (play_ng or play), or set PLAYSTDIN")
            player = [player_name, "-r", str(args.frequency), "-e", "signed", "-b", "8", "-c", "1", "-t", "raw", "-q", "-"]
        if not player:
            parser.error("PLAYSTDIN must contain a player command")

    if args.phonetic:
        phonemes = args.text.encode().strip()
    else:
        phonemes = subprocess.run(translator, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout.strip()
    if not phonemes:
        raise RuntimeError("no phonetic text to synthesize")
    print("Phonetic text:", phonemes.decode(errors="replace"), flush=True)
    narrator = [binary("narrator"), "-d", args.device, "-r", str(args.rate), "-p", str(args.pitch),
                "-m", str(args.mode), "-s", str(args.sex), "-f", str(args.frequency), "-"]
    # Narrator logs every emulated instruction; keep the log out of memory.
    with tempfile.TemporaryFile() as log:
        speech = subprocess.run(narrator, input=phonemes + b"\n", stdout=subprocess.PIPE, stderr=log)
        log.seek(0, os.SEEK_END)
        log.seek(max(0, log.tell() - 2048))
        tail = log.read()
    # The existing ReplyMsg completion handler exits 1 even on success.
    completed = speech.returncode == 0 or (
        speech.returncode == 1 and tail.rstrip().endswith(b"***** io_Error 0")
    )
    if not completed or not speech.stdout:
        raise RuntimeError(f"narrator failed (exit {speech.returncode}):\n{tail.decode(errors='replace')}")
    if args.output is not None:
        # Narrator emits signed 8-bit PCM; 8-bit PCM in WAV is unsigned.
        unsigned_pcm = speech.stdout.translate(bytes(value ^ 0x80 for value in range(256)))
        with wave.open(args.output, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(1)
            output.setframerate(args.frequency)
            output.writeframes(unsigned_pcm)
        print(f"Saved audio to {args.output}")
    else:
        subprocess.run(player, input=speech.stdout, check=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, wave.Error, subprocess.CalledProcessError) as error:
        print(f"say.py: {error}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
