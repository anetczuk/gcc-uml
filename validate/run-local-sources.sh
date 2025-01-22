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
source "$SCRIPT_DIR/_taskverify.sh"


GCC_COMMAND="g++"
source "$SCRIPT_DIR/../config.bash" || true


export PROJECT_COMMAND="${SCRIPT_DIR}/../src/gccuml/main.py"
export GCC_COMMAND


WORK_DIR="$SCRIPT_DIR/tmp/ws-local"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"


JOBS_NUM=6
SOURCES_ROOT_DIR="${SCRIPT_DIR}/../examples"
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

      *)  ARGS+=("$1")
          shift ;;
    esac
done


if [ ${#ARGS[@]} -gt 0 ]; then
	## single file mode
	srcfile="${ARGS[0]}"
	verify_source "$srcfile" "1 of 1"
	exit 0
fi


run_scan "$SOURCES_ROOT_DIR" "$JOBS_NUM" "$OUTPUT_FILE_PATH"

run_verify "$OUTPUT_FILE_PATH" "$JOBS_NUM" "$OUTPUT_FILE_PATH"
