#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


ARGS=()

VENV=false
USE_PROFILER=false
USE_PRINTHTML=false

SRC_FILES=()


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

      --mem_*)  PARAM=${1:2}
      			SRC_FILES+=("${PARAM}.cpp")
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
		"$SRC_DIR"/gccuml/main.py printhtml \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  -ii \
								  --outhtmldir "$BUILD_DIR/html-$SAMPLE_FILE" \
								  "${ARGS[@]}"
	fi

	OUT_DIAG_PATH="$BUILD_DIR/../${SAMPLE_FILE}.dot"

	if [ "$USE_PROFILER" = false ]; then
		FILE_CONTENT=""
# 		FILE_CONTENT=$(cat "$source_file")
# 		FILE_CONTENT=$(echo "$FILE_CONTENT" | sed 's/\t/    /g')
		
		"$SRC_DIR"/gccuml/main.py memlayout \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  --outpath "$OUT_DIAG_PATH" \
								  --graphnote "$FILE_CONTENT" \
								  "${ARGS[@]}"
# 								  -ii \
	else
		"$SRC_DIR"/../tools/profiler.sh --cprofile \
		"$SRC_DIR"/gccuml/main.py memlayout \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  --outpath "$OUT_DIAG_PATH" \
								  "${ARGS[@]}"
	fi
	set +x
	
	OUT_IMG_PATH="$BUILD_DIR/${SAMPLE_FILE}.svg"
	dot -Tsvg "$OUT_DIAG_PATH" -o "$OUT_IMG_PATH"

	echo "diagram output: file://${OUT_IMG_PATH}"
}


if [ ${#SRC_FILES[@]} -ne 0 ]; then
	for file_name in "${SRC_FILES[@]}"; do
		prepare_sample "$file_name"
	done

	exit 0
fi


# no files given - use all files
for src_file in "$SCRIPT_DIR"/src/*.cpp; do
	file_name=$(basename "${src_file}")
	prepare_sample "$file_name"
done

exit 0
