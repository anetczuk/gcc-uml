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


if [ $# -gt 0 ]; then
	## single file mode
	srcfile="$1"
	verify_source "$srcfile" "1 of 1"
	exit 0
fi


SOURCES_ROOT_DIR="${SCRIPT_DIR}/../examples"
JOBS_NUM=6
OUTPUT_FILE_PATH="${WORK_DIR}/sources-valid.txt"


run_scan "$SOURCES_ROOT_DIR" "$JOBS_NUM" "$OUTPUT_FILE_PATH"

run_verify "$OUTPUT_FILE_PATH" "$JOBS_NUM" "$OUTPUT_FILE_PATH"
