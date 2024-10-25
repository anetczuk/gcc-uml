#!/bin/bash

set -eu

## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


## 'source' is somehow simillar to C 'include'
# shellcheck disable=SC1090
source "$SCRIPT_DIR/../doc/generate_small.sh"
