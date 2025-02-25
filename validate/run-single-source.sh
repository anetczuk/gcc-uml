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


WORK_DIR="$SCRIPT_DIR/tmp/ws-single"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"


ARGS=()

while :; do
    if [ -z "${1+x}" ]; then
        ## end of arguments (prevents unbound argument error)
        break
    fi

    case "$1" in
      --*)			shift
      				;; # skip unknown argument

      *)  ARGS+=("$1")
          shift ;;
    esac
done


LOG_LEVEL="INFO"


## single file mode
srcfile="${ARGS[0]}"
verify_source "$srcfile" "1 of 1"

echo "completed"
