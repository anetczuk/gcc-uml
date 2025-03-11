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

      --ctrl_*)  PARAM=${1:2}
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


UTILS_PATH="$SCRIPT_DIR/../genutils.bash"
# shellcheck disable=SC1090
source "$UTILS_PATH"


SRC_DIR="$SCRIPT_DIR/../../src"

BUILD_DIR="$SCRIPT_DIR/build"

mkdir -p "$BUILD_DIR"


prepare_sample() {
	local SAMPLE_FILE="$1"

	cd "$BUILD_DIR"
	local source_file="$SCRIPT_DIR/src/$SAMPLE_FILE"
	compile_code "$source_file"

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


	COMMAND=""
	if [ "$USE_PROFILER" = false ]; then	
		COMMAND="$SRC_DIR/gccuml/main.py --exitloglevel ERROR ctrlflowgraph"
	else
		COMMAND="$SRC_DIR/../tools/profiler.sh --cprofile $SRC_DIR/gccuml/main.py ctrlflowgraph"
	fi

	OUT_PUML_PATH="$BUILD_DIR/../${SAMPLE_FILE}.puml"
	$COMMAND \
			  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
			  --reducepaths "$SCRIPT_DIR/" \
			  --engine "plantuml" \
			  --outpath "$OUT_PUML_PATH" \
			  "${ARGS[@]}"
# 			  -ii \

	OUT_DOT_PATH="$BUILD_DIR/../${SAMPLE_FILE}.dot"
	$COMMAND \
			  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
			  --reducepaths "$SCRIPT_DIR/" \
			  --engine "dot" \
			  --outpath "$OUT_DOT_PATH" \
			  "${ARGS[@]}"
# 			  -ii \

	set +x

 	OUT_PUML_DIAG="$BUILD_DIR/${SAMPLE_FILE}.puml.svg"
 	convert_puml "$OUT_PUML_PATH" "/tmp" || true
 	TMP_DIAG="/tmp/${SAMPLE_FILE}.svg"
 	cp "$TMP_DIAG" "$OUT_PUML_DIAG"

	convert_dot "$OUT_DOT_PATH" "$BUILD_DIR"
}


if [ ${#SRC_FILES[@]} -ne 0 ]; then
	# files passed
	handle_files "${SRC_FILES[@]}"
else
	# no files given - use all files
	handle_dir "$SCRIPT_DIR/src"	
fi

echo "completed"
