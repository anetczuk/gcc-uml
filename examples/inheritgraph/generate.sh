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


	if [ "$USE_PRINTHTML" = true ]; then
		set -x
		"$SRC_DIR"/gccuml/main.py printhtml \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  -ii \
								  --outpath "$BUILD_DIR/html-$SAMPLE_FILE" \
								  "${ARGS[@]}"
		set +x
	fi

	OUT_DIAG_PATH="$BUILD_DIR/../${SAMPLE_FILE}.puml"

	if [ "$USE_PROFILER" = false ]; then
		set -x
		"$SRC_DIR"/gccuml/main.py inheritgraph \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  --outpath "$OUT_DIAG_PATH" \
								  "${ARGS[@]}"
		set +x
	else
		set -x
		"$SRC_DIR"/../tools/profiler.sh --cprofile \
		"$SRC_DIR"/gccuml/main.py inheritgraph \
								  --rawfile "$BUILD_DIR/$SAMPLE_FILE.003l.raw" \
								  --reducepaths "$SCRIPT_DIR/" \
								  --outpath "$OUT_DIAG_PATH" \
								  "${ARGS[@]}"
		set +x
	fi

	convert_puml "$OUT_DIAG_PATH" "$BUILD_DIR"

	echo ""
}


## hardcoded conversion
prepare_yaml() {
	local ITEMS="$*"

	if [ "$ITEMS" == "" ]; then
		## if no arguments given then allow one iteration of loop to process all files
		ITEMS="-"
	fi

	for i in ${ITEMS}; do
	    if [ "$i" == "inherit_diamond1.cpp" ] || [ "$#" -eq 0 ]; then
	    	i="inherit_diamond1.cpp"
			prepare_config "${SCRIPT_DIR}/src/${i}.yaml"
			convert_puml "$SCRIPT_DIR/${i}.inherit.puml" "$BUILD_DIR"
			convert_dot "$SCRIPT_DIR/${i}.memlay.dot" "$BUILD_DIR"
			echo ""
	    fi
	    if [ "$i" == "inherit_diamond2.cpp" ] || [ "$#" -eq 0 ]; then
	    	i="inherit_diamond2.cpp"
			prepare_config "${SCRIPT_DIR}/src/${i}.yaml"
			convert_puml "$SCRIPT_DIR/${i}.inherit.puml" "$BUILD_DIR"
			convert_dot "$SCRIPT_DIR/${i}.memlay.dot" "$BUILD_DIR"
			echo ""
	    fi
	done
}


if [ ${#SRC_FILES[@]} -ne 0 ]; then
	# files passed
	handle_files "${SRC_FILES[@]}"
else
	# no files given - use all files
	handle_dir "$SCRIPT_DIR/src"	
fi

echo "completed"
