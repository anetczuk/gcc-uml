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


USE_PROFILER=0
if [[ $* == *--profile* ]]; then
	USE_PROFILER=1
fi

# ===================================

SRC_DIR="$SCRIPT_DIR/../../src"


prepare_sample() {
	local SAMPLE_FILE="$1"
	local SAMPLE_PATH="$SCRIPT_DIR/$1"
	
	local OUT_DIR="$SCRIPT_DIR/output-$SAMPLE_FILE"
	rm -rf "$OUT_DIR"
	mkdir -p "$OUT_DIR"

	cd "$SCRIPT_DIR/../../src/"

	"$SRC_DIR"/gcclangrawparser/main.py tools \
										--rawfile "$SAMPLE_PATH" \
										--outtypefields "$OUT_DIR/fields-$SAMPLE_FILE.json" \
										--outtreetxt "$OUT_DIR/graph-$SAMPLE_FILE.txt"

	if [ $USE_PROFILER -eq 1 ]; then
		"$SRC_DIR"/../tools/profiler.sh --cprofile \
		"$SRC_DIR"/gcclangrawparser/main.py printhtml \
											--progressbar=False \
											--rawfile "$SAMPLE_PATH" \
											--genentrygraphs=False \
											--outhtmldir "$OUT_DIR/html-$SAMPLE_FILE"
	else
		"$SRC_DIR"/gcclangrawparser/main.py printhtml \
											--rawfile "$SAMPLE_PATH" \
											--genentrygraphs=False \
											--outhtmldir "$OUT_DIR/html-$SAMPLE_FILE"
	fi
}


if [[ $* == *--empty2functs* ]]; then
	prepare_sample "empty2functs.cpp.raw"
	exit 0
fi


prepare_sample "empty2functs.cpp.raw"
