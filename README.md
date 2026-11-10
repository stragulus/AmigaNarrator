# AmigaNarrator

Commodore Amiga narrator.device emulator

Note: This is __detached fork__, as the upstream repository has been deleted.
      The code is almost entirely by [Arthur Choung];
      the changes made since the upstream version are:
 - add support for the [translator42] library (TranslateAs)
 - remove local Musashi copy (added as git submodule)
 - some minor project/build cleanup


## Background

The narrator.device is a speech synthesizer for the Commodore Amiga written by
Mark Barton and Joseph Katz. From what I understand, Mark Barton was responsible
for the speech synthesis, while Joseph Katz handled the systems integration. This
was more or less the same speech synthesizer as the original MacinTalk on the
very first Macs. It was the successor to SAM (Software Automatic Mouth) for the
Apple II, Commodore 64, and Atari 8-bit computers.

For details, listen to an interview with Mark Barton on ANTIC The Atari 8-bit
Podcast.

https://ataripodcast.libsyn.com/antic-interview-385-software-automatic-mouth-mark-barton


## Overview

Similar to vamos (Virtual AmigaOS runtime), this is a tool that will run the
code from the narrator.device and translator.library. The actual code is
emulated using the Musashi 680x0 CPU emulator, while just enough of the OS
is simulated by trapping the exec.library calls.


## Example

Cover of Robots (The Humans Are Dead) - Flight of the Conchords

Performed by Amiga narrator.device (and YM2413)

Listen on YouTube:

https://www.youtube.com/watch?v=kT68O6jtOVY


## Build

The build needs a C compiler, GNU Make, the C standard/math libraries, and the
Musashi sources pinned by this repository's Git submodule. No Amiga files or
audio player are needed to compile.

From the repository root, initialize the submodule (also required for Docker):

```sh
git submodule update --init --recursive
```

For a new checkout, `git clone --recurse-submodules <repository-url>` does this
automatically. A plain clone or source ZIP does not include Musashi's sources.
An error such as `m68k.h: No such file or directory` usually means the submodule
has not been initialized.

### Docker build (no host compiler needed)

With Docker installed and running, build the image and export the executables
into the host's `bin/` directory:

```sh
docker build -t amiganarrator-build .
mkdir -p bin
docker run --rm --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$PWD/bin,target=/out" amiganarrator-build
```

The second command runs the image's default copy command. It writes `narrator`,
`translator`, and `translateas` into `./bin/`, owned by your host user. Existing
files with those names are replaced. The build installs its compiler inside
Docker and links the executables statically, so no Alpine libraries are needed
on the host. The image is reusable; run the export command again to copy them
to another directory (create it first and change the mount's `source`).

These are **Linux executables for the architecture Docker builds for**. They
can run directly on a Linux host of that architecture. On macOS or Windows,
run them inside the image instead, mounting the repository for runtime files:

```sh
docker run --rm --mount "type=bind,source=$PWD,target=/work" -w /work \
  --entrypoint /artifacts/translator amiganarrator-build "Hello world."
```

This invocation requires `Libs/translator.library` on the host as described
below. Use `/artifacts/narrator` or `/artifacts/translateas` as the entrypoint
for the other tools; add `-i` to `docker run` when feeding standard input.

### Native build

On Debian/Ubuntu, install the build tools with
`sudo apt-get install build-essential git`. On other systems, install the
equivalent C compiler and GNU Make packages. Then, after initializing Musashi:

```sh
make
```

This creates `bin/narrator`, `bin/translator`, and `bin/translateas`.
Use plain `make`: the opcode generator's source/header rule is not safe for
parallel builds. Run `make clean` before rebuilding with a different compiler
or compiler flags.

## Run

Run from the repository root so the default runtime paths resolve correctly.
You must supply `Devs/narrator.device` and `Libs/translator.library` from your
Amiga installation; they are not included in this repository or Docker image.
For the alternate `translateas` tool, supply the translator42 library as
`Libs/v33_translator.library` and its accent files in `Accents/` (see
[translator42]). These are runtime dependencies, separate from the build tools.

### Extract runtime files from a Workbench 1.3 disk image

Provide your own **Workbench 1.3 Workbench disk in uncompressed `.adf` format**.
Only Workbench 1.3 is supported by this extraction workflow. Use the Workbench
disk (Disk 1), not the Extras disk (Disk 2). Images are not supplied or downloaded.

From the repository root, build the separate extractor image, set `WB13_IMAGE`
to the absolute path of your ADF, and run:

```sh
docker build -f Dockerfile.workbench13 -t amiganarrator-workbench13 .
WB13_IMAGE="/absolute/path/to/Workbench 1.3.adf"
mkdir -p Devs Libs
docker run --rm --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$WB13_IMAGE,target=/input/workbench.adf,readonly" \
  --mount "type=bind,source=$PWD,target=/out" \
  amiganarrator-workbench13 /input/workbench.adf
```

The quoted mounts support paths containing spaces. The input image is mounted
read-only at runtime and is never copied into the Docker image. The extractor
uses [amitools' xdftool](https://amitools.readthedocs.io/en/latest/tools/xdftool.html)
to copy only `Devs/narrator.device` and `Libs/translator.library` into the host
repository, owned by your host user. Existing files at those two paths are
replaced. Both paths are ignored by Git. To export elsewhere, create a directory
and use its absolute path as the `/out` mount's `source`.

After building/exporting the executables as above, test the complete pipeline:

```sh
./bin/translator "Hello world." > hello_world.txt
./bin/narrator - < hello_world.txt > hello_world.s8
```

The current `narrator` completion handler exits with status 1 even when the
Amiga request succeeds (`io_Error 0` in stderr) and PCM audio is written. This
existing behavior also occurs with the tested Workbench 1.3 files.

This supplies the runtime files for `translator` and `narrator`. Workbench 1.3
does not supply translator42 or its accents for the alternate `translateas` tool.

### Translate and synthesize

First, use `translator` to convert English text to phonetic text.

Then, use `narrator` to convert phonetic text to PCM samples.

The PCM samples are S8 (mono signed 8-bit) at 22200 Hz.

Don't forget to end your sentences with a period.

Run `./bin/narrator` or `./bin/translator` with no arguments, or
`./bin/translateas --help`, for a list of options such as pitch and rate.

The `translateas` command is an alternate to the `translator` binary
that uses the [translator42] library.

### Test playback with say.sh

The `./say.sh` script runs `translator` (or `translateas` when an accent is
specified), passes the phonetic string to `narrator`, and plays the PCM samples
with [SoX_ng]'s `play_ng` on the host.

Install your distribution's `sox` package for playback. On distributions that
package SoX_ng as `sox`, this provides `play_ng`. Some distributions provide
only `play` instead, such as
[Debian](https://packages.debian.org/en/trixie/arm64/sox/filelist).

After exporting the executables to `bin/` and extracting the Workbench 1.3
runtime files into `Devs/` and `Libs/`, run from the repository root:

```sh
sh ./say.sh "Hello world."
```

You should hear “Hello world.” through your host's configured audio output.
Keep the final period. With Workbench 1.3, omit the optional accent argument;
accents require the separate translator42 library and accent files.

If `play_ng` is unavailable but `play` is installed, select it explicitly:

```sh
PLAYSTDIN='play -r 22200 -e signed -b 8 -t raw -q -' \
  sh ./say.sh "Hello world."
```

Run this on a host with working audio output; the Docker images above do not
need audio-device access.

### Adjust the voice with say.py

`say.py` requires Python 3 and the same executables and runtime files as
`say.sh`. Playback uses the same host audio setup; saving a WAV file needs no
audio player. It accepts narrator options, with matching short flags:

```sh
python3 ./say.py "Hello world."
python3 ./say.py --rate 200 --pitch 180 --sex 1 --mode 1 "Hello world."
```

The second example uses a faster, higher-pitched female voice with robotic
intonation. Options are:

| Option | Range / meaning | Default |
| --- | --- | --- |
| `-r`, `--rate` | 40-400 words per minute | 150 |
| `-p`, `--pitch` | 65-320 | 110 |
| `-s`, `--sex` | 0=male, 1=female | 0 |
| `-m`, `--mode` | 0=natural, 1=robotic | 0 |
| `-f`, `--frequency` | 5000-28000 Hz sample rate | 22200 |
| `-d`, `--device` | Path to narrator.device | `DEV_PATH` or `./Devs/narrator.device` |

The script automatically uses `play_ng`, falling back to `play`, and sets the
player's sample rate to match `--frequency`. It also honors `say.sh`'s
`OUTDIR`, `EXE`, `LIB_PATH`, `DEV_PATH`, `ACCENT_DIR` and `PLAYSTDIN` environment
variables. A custom `PLAYSTDIN` must specify the matching sample rate itself;
it is split into arguments without shell expansion or shell pipelines.

Like `say.sh`, an optional second positional argument selects a translator42
accent: `python3 ./say.py "Hello world." american`. Omit it for Workbench 1.3.
Use `python3 ./say.py --help` for all options.

To supply narrator phonemes directly, use `--phonetic` to skip translation:

```sh
python3 ./say.py --phonetic --rate 200 --pitch 180 "/HEH4LOW WER4LD."
```

This mode requires only the `narrator` executable and `Devs/narrator.device`
for synthesis; no translator executable or library is needed. Voice options
still apply. An accent argument cannot be combined with `--phonetic`.

To save the generated audio instead of playing it, use `-o` / `--output`:

```sh
python3 ./say.py --output hello.wav "Hello world."
python3 ./say.py --phonetic --pitch 180 --frequency 16000 \
  -o hello-phonetic.wav "/HEH4LOW WER4LD."
```

This writes a mono 8-bit PCM WAV at the selected sample rate (22200 Hz by
default), replacing an existing output file. WAV output uses Python's standard
library, so no additional dependencies, SoX installation or audio device are
needed. In this mode `PLAYSTDIN` is ignored.

### Run each tool separately

```
$ ./bin/translator "Hello world." > hello_world.txt
```

The file 'hello_world.txt' should contain:

```
/HEH4LOW WER4LD.
```

```
$ cat hello_world.txt | ./bin/narrator - > hello_world.s8
```

It will run faster if stderr is redirected to /dev/null:

```
$ cat hello_world.txt | ./bin/narrator - 2>/dev/null > hello_world.s8
```

On Linux, [SoX_ng] can be used to play the file:

```
$ play_ng -r 22200 -e signed -b 8 -t raw hello_world.s8
```

## narrator.device

This file will be loaded from `./Devs/` when `narrator` is run.
An alternative file can be specified using the `-d` flag on `narrator`
(for `./say.sh` you have to set/export `DEV_PATH`).

It has been tested with the narrator.device from:

- Workbench 1.0
- Workbench 1.1
- Workbench 1.2
- Workbench 1.3 (same as 1.2)
- Workbench 2.04
- Workbench 2.05 (same as 2.04)

This file is not supplied.


## translator.library

This file will be loaded from `./Libs/` when `translator` is run.
An alternative file can be specified using the `-l` flag on `translator`
(for `./say.sh` you have to set/export `LIB_PATH`).

It has been tested with the translator.library from:

- Workbench 1.0
- Workbench 1.1
- Workbench 1.2
- Workbench 1.3 (same as 1.2)
- Workbench 1.3.3
- Workbench 2.04
- Workbench 2.05 (same as 2.04)

This file is not supplied.


## Resources

#### Markus Wandel's Amiga Exec disassembly
https://wandel.ca/homepage/execdis/

#### Amiga Developer Docs
http://amigadev.elowar.com/
 
#### Hunk File Format
http://amiga-dev.wikidot.com/file-format:hunk

#### vamos and hunktool from amitools by Christian Vogelgsang
https://github.com/cnvogelg/amitools

#### Musashi 680x0 CPU emulator by Karl Stenerud
https://github.com/kstenerud/Musashi


## Legal

The original source is Copyright (C) 2023 Arthur Choung
and released under the GNU General Public License v3.0.

The translateas.c is Copyright (C) 2024 Nico Bendlin
and released under the GNU General Public License v3.0 or later.

Additional files are Copyright (C) 2026 Nico Bendlin
and released under the BSD Zero Clause License.

For details on the licenses, refer to the [REUSE](REUSE.toml) file.

[![REUSE status](https://api.reuse.software/badge/github.com/nicodex/AmigaNarrator)](https://api.reuse.software/info/github.com/nicodex/AmigaNarrator)

[Arthur Choung]: https://github.com/arthurchoung
[translator42]: https://aminet.net/package/util/libs/translator42
[SoX_ng]: https://codeberg.org/sox_ng/sox_ng

