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


PROJECT_COMMAND="${SCRIPT_DIR}/../src/gccuml/main.py"


"$PROJECT_COMMAND" printhtml \
					  --rawfile "$1" \
					  -ii \
					  --outpath "${1}-html"
