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

BUILD_DIR="$SCRIPT_DIR/build"

mkdir -p "$BUILD_DIR"


prepare_sample() {
	local SAMPLE_FILE="$1"

	cd "$BUILD_DIR"

	local source_file="$SCRIPT_DIR/src/$SAMPLE_FILE"
	echo "compiling file: $source_file"
	g++ -fdump-lang-raw -c "$source_file"

	cd "$SCRIPT_DIR/../../src/"

	if [ $USE_PROFILER -eq 1 ]; then
		"$SRC_DIR"/../tools/profiler.sh --cprofile \
		"$SRC_DIR"/gcclangrawparser/main.py --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
											--outtypefields "$SCRIPT_DIR/fields-$SAMPLE_FILE.json" \
											--reducepaths "$SCRIPT_DIR/" \
											--outtreetxt "$SCRIPT_DIR/graph-$SAMPLE_FILE.txt" \
											--outbiggraph "$BUILD_DIR/graph-$SAMPLE_FILE.png" \
											--outhtmldir "$BUILD_DIR/html-$SAMPLE_FILE"
	else
		"$SRC_DIR"/gcclangrawparser/main.py --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
											--outtypefields "$SCRIPT_DIR/fields-$SAMPLE_FILE.json" \
											--reducepaths "$SCRIPT_DIR/" \
											--outtreetxt "$SCRIPT_DIR/graph-$SAMPLE_FILE.txt" \
											--outbiggraph "$BUILD_DIR/graph-$SAMPLE_FILE.png" \
											--outhtmldir "$BUILD_DIR/html-$SAMPLE_FILE"
	fi
}


if [[ $* == *--emptymain* ]]; then
	prepare_sample "emptymain.cpp"
	exit 0
fi
if [[ $* == *--emptyfunct.cpp* ]]; then
	prepare_sample "emptyfunct.cpp"
	exit 0
fi
if [[ $* == *--empty2functs* ]]; then
	prepare_sample "empty2functs.cpp"
	exit 0
fi
if [[ $* == *--emptyns* ]]; then
	prepare_sample "emptyns.cpp"
	exit 0
fi
if [[ $* == *--source1* ]]; then
	prepare_sample "source1.cpp"
	exit 0
fi
if [[ $* == *--source2* ]]; then
	prepare_sample "source2.c"
	exit 0
fi


prepare_sample "emptymain.cpp"
prepare_sample "emptyfunct.cpp"
prepare_sample "empty2functs.cpp"
prepare_sample "emptyns.cpp"
prepare_sample "source1.cpp"
prepare_sample "source2.c"
