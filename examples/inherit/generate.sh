#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


ARGS=()

VENV=false
USE_PROFILER=false
USE_PRINTHTML=false

SRC_SOURCE1=false


while :; do
    if [ -z "${1+x}" ]; then
        ## end of arguments (prevents unbound argument error)
        break
    fi

    case "$1" in
      --venv)     VENV=true 
                  shift ;;
      --profile)  USE_PROFILER=true 
                  shift ;;
      --printhtml)  USE_PRINTHTML=true 
                    shift ;;

      --source1)  SRC_SOURCE1=true 
                  shift ;;

      *)  ARGS+=("$1")
          shift ;;
    esac
done


if [ "$VENV" = true ]; then
	## run under venv
	VENV_DIR="$SCRIPT_DIR/../../venv"
	"$VENV_DIR"/activatevenv.sh "$0; exit"
	exit 0
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

	set -x

	if [ "$USE_PRINTHTML" = true ]; then
		"$SRC_DIR"/gcclangrawparser/main.py printhtml \
											--rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
											--reducepaths "$SCRIPT_DIR/" \
											-ii \
											--outhtmldir "$BUILD_DIR/html-$SAMPLE_FILE" \
											"${ARGS[@]}"
	fi

	OUT_DIAG_PATH="$BUILD_DIR/inherit-${SAMPLE_FILE}.puml"

	if [ "$USE_PROFILER" = false ]; then
		"$SRC_DIR"/gcclangrawparser/main.py inheritgraph \
											--rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
											--reducepaths "$SCRIPT_DIR/" \
											--outpath "$OUT_DIAG_PATH" \
											"${ARGS[@]}"
	else
		"$SRC_DIR"/../tools/profiler.sh --cprofile \
		"$SRC_DIR"/gcclangrawparser/main.py inheritgraph \
											--rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
											--reducepaths "$SCRIPT_DIR/" \
											--outpath "$OUT_DIAG_PATH" \
											"${ARGS[@]}"
	fi
	set +x
	
	plantuml "$OUT_DIAG_PATH"
}


if [ "$SRC_SOURCE1" = true ]; then
	prepare_sample "source1.cpp"
	exit 0
fi


prepare_sample "source1.cpp"
