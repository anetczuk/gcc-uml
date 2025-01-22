#!/bin/bash
#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


source "$SCRIPT_DIR/_parallelwork.sh"

source "$SCRIPT_DIR/_task.sh"
source "$SCRIPT_DIR/_taskscan.sh"
source "$SCRIPT_DIR/_taskverify.sh"


GCC_COMMAND="g++"


cfg_path="${SCRIPT_DIR}/../config.bash"
cfg_path="$(realpath "${cfg_path}")"
# shellcheck disable=SC1090
source "$cfg_path" || true


export PROJECT_COMMAND="${SCRIPT_DIR}/../src/gccuml/main.py"
export GCC_COMMAND


if [ $# -gt 0 ]; then
	## single file mode
	srcfile="$1"
	process_file "$srcfile" "1 of 1"
	exit 0
fi


JOBS_NUM=6
WORK_DIR="$SCRIPT_DIR/tmp/ws-gcc"
OUTPUT_FILE_PATH="${WORK_DIR}/sources-valid.txt"


mkdir -p "$WORK_DIR"
cd "$WORK_DIR"


if [ -z ${GCC_TESTS_DIR+x} ]; then
 	echo "required variable GCC_TESTS_DIR not defined in ${cfg_path}"

	GCC_TAR_PATH="${WORK_DIR}/gcc.tar.xz"
	if [ ! -f "$GCC_TAR_PATH" ]; then
		echo "downloading gcc sources"
		wget http://ftp.gnu.org/gnu/gcc/gcc-14.2.0/gcc-14.2.0.tar.xz -O "$GCC_TAR_PATH"
	fi

	GCC_SRC_ROOT_DIR="/tmp/gcc_src"
	mkdir -p "$GCC_SRC_ROOT_DIR"

	gcc_dirs=("$GCC_SRC_ROOT_DIR"/*/)
	GCC_TESTS_DIR="${gcc_dirs[0]}gcc/testsuite"

	if [ ! -d "$GCC_TESTS_DIR" ]; then
		echo "extracting tar to $GCC_SRC_ROOT_DIR"
		tar -xf "$GCC_TAR_PATH" -C "$GCC_SRC_ROOT_DIR"
	fi

	gcc_dirs=("$GCC_SRC_ROOT_DIR"/*/)
	GCC_TESTS_DIR="${gcc_dirs[0]}gcc/testsuite"

	if [ ! -d "$GCC_TESTS_DIR" ]; then
		echo "unable to find tests directory: $GCC_TESTS_DIR"
		exit 1
	fi

	echo "found gcc tests dir: $GCC_TESTS_DIR"
fi


run_scan "$GCC_TESTS_DIR" "$JOBS_NUM" "$OUTPUT_FILE_PATH"

run_verify "$OUTPUT_FILE_PATH" "$JOBS_NUM" "$OUTPUT_FILE_PATH"
