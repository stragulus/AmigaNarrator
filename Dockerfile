# SPDX-FileCopyrightText: 2026 AmigaNarrator contributors
# SPDX-License-Identifier: 0BSD
FROM alpine:3.22 AS build
RUN apk add --no-cache build-base
WORKDIR /src
COPY Makefile cpuconf.h narrator.c translator.c translateas.c ./
COPY Musashi/ ./Musashi/
RUN test -f Musashi/m68k.h || \
    { echo 'Missing Musashi sources: run git submodule update --init --recursive' >&2; exit 1; }
# Serial make avoids concurrent generation of Musashi's opcode source/header.
RUN make CC=gcc CFLAGS='-std=c99 -O2 -IMusashi' LDFLAGS=-static

FROM alpine:3.22 AS artifacts
COPY --from=build /src/bin/ /artifacts/
# Bind a host directory at /out to export the three Linux executables.
CMD ["cp", "/artifacts/narrator", "/artifacts/translator", "/artifacts/translateas", "/out/"]
