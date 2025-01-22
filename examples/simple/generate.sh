#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


ARGS=()

VENV=false
USE_PROFILER=false

SRC_EMPTYMAIN=false
SRC_EMPTYFUNCT=false
SRC_EMPTY2FUNCTS=false
SRC_EMPTYNS=false
SRC_SOURCE1=false
SRC_SOURCE2=false


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

      --emptymain)  SRC_EMPTYMAIN=true 
                  	shift ;;
      --emptyfunct)  SRC_EMPTYFUNCT=true 
                  	 shift ;;
      --empty2functs)  SRC_EMPTY2FUNCTS=true 
                  	   shift ;;
      --emptyns)  SRC_EMPTYNS=true 
                  shift ;;
      --source1)  SRC_SOURCE1=true 
                  shift ;;
      --source2)  SRC_SOURCE2=true 
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

	## generate various data
	"$SRC_DIR"/gccuml/main.py tools \
							  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
							  --reducepaths "$SCRIPT_DIR/" \
							  --outtypefields "$SCRIPT_DIR/fields-$SAMPLE_FILE.json" \
							  --outtreetxt "$SCRIPT_DIR/graph-$SAMPLE_FILE.txt"
# 							  --outbiggraph "$BUILD_DIR/graph-$SAMPLE_FILE.png" \

	## print html
	if [ "$USE_PROFILER" = false ]; then
		"$SRC_DIR"/gccuml/main.py printhtml \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  --outpath "$BUILD_DIR/html-$SAMPLE_FILE" \
								  "${ARGS[@]}"
	else
		"$SRC_DIR"/../tools/profiler.sh --cprofile \
		"$SRC_DIR"/gccuml/main.py printhtml \
								  --progressbar=False \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  --outpath "$BUILD_DIR/html-$SAMPLE_FILE" \
								  "${ARGS[@]}"
	fi
	set +x
}


if [ "$SRC_EMPTYMAIN" = true ]; then
	prepare_sample "emptymain.cpp"
	exit 0
fi
if [ "$SRC_EMPTYFUNCT" = true ]; then
	prepare_sample "emptyfunct.cpp"
	exit 0
fi
if [ "$SRC_EMPTY2FUNCTS" = true ]; then
	prepare_sample "empty2functs.cpp"
	exit 0
fi
if [ "$SRC_EMPTYNS" = true ]; then
	prepare_sample "emptyns.cpp"
	exit 0
fi
if [ "$SRC_SOURCE1" = true ]; then
	prepare_sample "source1.cpp"
	exit 0
fi
if [ "$SRC_SOURCE2" = true ]; then
	prepare_sample "source2.c"
	exit 0
fi


prepare_sample "emptymain.cpp"
prepare_sample "emptyfunct.cpp"
prepare_sample "empty2functs.cpp"
prepare_sample "emptyns.cpp"
prepare_sample "source1.cpp"
prepare_sample "source2.c"
