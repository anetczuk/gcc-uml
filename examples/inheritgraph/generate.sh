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

      --inherit_*)  PARAM=${1:2}
      				SRC_FILES+=("${PARAM}.cpp")
                    shift ;;

      --cpp_*)  PARAM=${1:2}
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


GCC_COMMAND="g++"

CONFIG_PATH="$SRC_DIR/../config.bash"
if [ -f "$CONFIG_PATH" ]; then
	# shellcheck disable=SC1090
	source "$CONFIG_PATH"
fi


prepare_sample() {
	local SAMPLE_FILE="$1"

	cd "$BUILD_DIR"

	local source_file="$SCRIPT_DIR/src/$SAMPLE_FILE"
	echo "compiling file: $source_file"
	$GCC_COMMAND -fdump-lang-raw -c "$source_file"
# 	$GCC_COMMAND -fdump-tree-original="${SAMPLE_FILE}.005t.original" -c "$source_file"
# 	$GCC_COMMAND -fdump-tree-original-raw="${SAMPLE_FILE}.005t.original.raw" -c "$source_file"
# 	$GCC_COMMAND -fdump-tree-all -c "$source_file"

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

	OUT_DIAG_PATH="$BUILD_DIR/../${SAMPLE_FILE}.puml"

	if [ "$USE_PROFILER" = false ]; then
		"$SRC_DIR"/gccuml/main.py inheritgraph \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  --outpath "$OUT_DIAG_PATH" \
								  "${ARGS[@]}"
	else
		"$SRC_DIR"/../tools/profiler.sh --cprofile \
		"$SRC_DIR"/gccuml/main.py inheritgraph \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  --outpath "$OUT_DIAG_PATH" \
								  "${ARGS[@]}"
	fi
	set +x
	
	plantuml -tsvg "$OUT_DIAG_PATH" -o "$BUILD_DIR"

	OUT_DIAG="$BUILD_DIR"/$(basename "${OUT_DIAG_PATH/puml/svg}")
	echo "diagram output: file://${OUT_DIAG}"
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
