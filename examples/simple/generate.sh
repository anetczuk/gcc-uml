#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


if [[ $* == *--venv* ]]; then
	## run under venv
	VENV_DIR="$SCRIPT_DIR/../../venv"
	"$VENV_DIR"/activatevenv.sh "$0; exit"
	exit 0
fi


# ===================================


SRC_DIR="$SCRIPT_DIR/../../src"

BUILD_DIR="$SCRIPT_DIR/build"


mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"


for source_file in "$SCRIPT_DIR"/*.c*; do
	echo "compiling file: $source_file"
	g++ -fdump-lang-raw -c "$source_file"
done


"$SRC_DIR"/gcclangrawparser/main.py --rawfile "$BUILD_DIR"/source2.c.003l.raw \
									--outtypefields "$SCRIPT_DIR"/fields.json \
									--outhtmldir "$BUILD_DIR"/html 
