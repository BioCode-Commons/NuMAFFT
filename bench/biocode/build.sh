#!/bin/sh
# Build the two pinned revisions with the same compiler and flags.
set -eu
root=${1:?Usage: CC=gcc ./build.sh /absolute/path/to/new-build-directory}
case "$root" in /*) ;; *) printf 'Use an absolute build directory.\n' >&2; exit 1 ;; esac
compiler=${CC:-gcc}
flags=${CFLAGS:--O3 -ffp-contract=off -std=c99}
jobs=${JOBS:-4}
mkdir -p "$root"
git clone https://gitlab.com/sysimm/mafft.git "$root/upstream-source"
git -C "$root/upstream-source" checkout --detach ee9799916df6a5d5103d46d54933f8eb6d28e244
git clone https://github.com/yih0nk/fast-mafft.git "$root/optimized-source"
git -C "$root/optimized-source" checkout --detach 6474c62da49ca3af73bbb7b05287bbbb4a2036e5
"$compiler" --version > "$root/compiler.txt"
build() {
    source_dir=$1
    prefix=$2
    log=$3
    make -C "$source_dir/core" clean > "$log" 2>&1
    make -C "$source_dir/core" -j"$jobs" CC="$compiler" CFLAGS="$flags" PREFIX="$prefix" >> "$log" 2>&1
    make -C "$source_dir/core" install CC="$compiler" CFLAGS="$flags" PREFIX="$prefix" >> "$log" 2>&1
    "$prefix/bin/mafft" --version
    grep 'prefix=/' "$prefix/bin/mafft"
}
build "$root/upstream-source" "$root/baseline" "$root/baseline-build.log"
build "$root/optimized-source/fast-mafft-src" "$root/optimized" "$root/optimized-build.log"
