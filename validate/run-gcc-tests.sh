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


# shellcheck disable=SC1091
source "$SCRIPT_DIR/_parallelwork.sh"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/_task.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_taskscan.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_workcmd.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_taskverify.sh"


GCC_COMMAND="g++"


cfg_path="${SCRIPT_DIR}/../config.bash"
cfg_path="$(realpath "${cfg_path}")"
# shellcheck disable=SC1090
source "$cfg_path" || true


export PROJECT_COMMAND="${SCRIPT_DIR}/../src/gccuml/main.py"
export GCC_COMMAND


WORK_DIR="$SCRIPT_DIR/tmp/ws-gcc"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"


JOBS_NUM=6
OUTPUT_FILE_PATH="${WORK_DIR}/sources-valid.txt"


ARGS=()

while :; do
    if [ -z "${1+x}" ]; then
        ## end of arguments (prevents unbound argument error)
        break
    fi

    case "$1" in
      -j=*)			JOBS_NUM="${1#*=}"
      				shift # past argument=value
      				;;

      --*)			shift
      				;; # skip unknown argument

      *)  ARGS+=("$1")
          shift ;;
    esac
done


if [ ${#ARGS[@]} -gt 0 ]; then
	## single file mode
	srcfile="${ARGS[0]}"
	verify_source "$srcfile" "1 of 1"
	echo "completed"
	exit 0
fi


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
