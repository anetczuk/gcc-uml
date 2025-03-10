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


convert_dot() {
	local DOT_FILE="$1"

	base_name=$(basename "$DOT_FILE")
	OUT_IMG_PATH="$BUILD_DIR/${base_name}.svg"
	dot -Tsvg "$DOT_FILE" -o "$OUT_IMG_PATH"

	echo "diagram output: file://${OUT_IMG_PATH}"
}


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
								  --outpath "$BUILD_DIR/html-$SAMPLE_FILE" \
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


## proper path
prepare_config() {
	local SAMPLE_FILE="$1"

	cd "$BUILD_DIR"

	local config_file="$SAMPLE_FILE"
	cd "$SCRIPT_DIR/../../src/"

	set -x

	OUT_DIAG_PATH="$BUILD_DIR/../${SAMPLE_FILE}.dot"

	if [ "$USE_PROFILER" = false ]; then
		FILE_CONTENT=""
# 		FILE_CONTENT=$(cat "$config_file")
# 		FILE_CONTENT=$(echo "$FILE_CONTENT" | sed 's/\t/    /g')
		
		"$SRC_DIR"/gccuml/main.py config \
								  --path "$config_file"
	else
		"$SRC_DIR"/../tools/profiler.sh --cprofile \
		"$SRC_DIR"/gccuml/main.py config \
								  --path "$config_file"
	fi
	set +x
}


## hardcoded conversion
prepare_yaml() {
	local ITEMS="$@"

	for i in "${ITEMS}"; do
	    if [ "$i" == "mem_padding.cpp" ] || [ "$#" -eq 0 ]; then
			prepare_config "$SCRIPT_DIR"/src/mem_padding.cpp.yaml
			convert_dot "$SCRIPT_DIR/mem_padding_1.dot"
			convert_dot "$SCRIPT_DIR/mem_padding_2.dot"
	    fi
	done
}


if [ ${#SRC_FILES[@]} -ne 0 ]; then
	for file_name in "${SRC_FILES[@]}"; do
		prepare_sample "$file_name"
	done

	prepare_yaml "${SRC_FILES[@]}"

	exit 0
fi


# no files given - use all files
for src_file in "$SCRIPT_DIR"/src/*.cpp; do
	file_name=$(basename "${src_file}")
	prepare_sample "$file_name"
done

prepare_yaml
