#!/bin/bash

set -eu


## =====================================


GCC_COMMAND="g++"

## works both under bash and sh
_GENUTILS_DIR=$(dirname "$(readlink -f "$0")")
CONFIG_PATH="$_GENUTILS_DIR/../../config.bash"
if [ -f "$CONFIG_PATH" ]; then
	# shellcheck disable=SC1090
	source "$CONFIG_PATH"
fi


## =====================================


# $1 - source path to compile
compile_code() {
	local source_file="$1"

	echo "compiling file: $source_file"
	$GCC_COMMAND -fdump-lang-raw -c "$source_file"
# 	$GCC_COMMAND -fdump-tree-original="${SAMPLE_FILE}.005t.original" -c "$source_file"
# 	$GCC_COMMAND -fdump-tree-original-raw="${SAMPLE_FILE}.005t.original.raw" -c "$source_file"
# 	$GCC_COMMAND -fdump-tree-all -c "$source_file"
}


# $1 - path to puml file
# $2 - output dir
convert_puml() {
	local PUML_FILE="$1"
	local OUT_DIR="$2"
	local OUT_DIAG="$OUT_DIR"/$(basename "${PUML_FILE/puml/svg}")
	echo "converting plantuml diagram $PUML_FILE to $OUT_DIAG"

	plantuml -tsvg "$PUML_FILE" -o "$OUT_DIR"

	echo "diagram output: file://${OUT_DIAG}"
}


# $1 - path to dot file
# $2 - output dir
convert_dot() {
	local DOT_FILE="$1"
	local OUT_DIR="$2"

	local base_name=$(basename "$DOT_FILE")
	local OUT_IMG_PATH="$OUT_DIR/${base_name}.svg"
	echo "converting dot diagram $DOT_FILE to $OUT_IMG_PATH"

	dot -Tsvg "$DOT_FILE" -o "$OUT_IMG_PATH"

	echo "diagram output: file://${OUT_IMG_PATH}"
}


# $1 - path to config yaml file
prepare_config() {
	local config_file="$1"

	cd "$SCRIPT_DIR/../../src/"

	set -x

	if [ "$USE_PROFILER" = false ]; then
# 		FILE_CONTENT=""
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


## redefine
prepare_sample() {
	echo "no proper prepare_sample function defined"
	exit 1
}


## redefine if needed
prepare_yaml() {
	echo "no config yaml files to process"
}


# $1 - sources list
handle_files() {
	local SRC_FILES="$*"

	for file_name in ${SRC_FILES[@]}; do
		prepare_sample "$file_name"
	done

	prepare_yaml "${SRC_FILES[@]}"
}


# $1 - dir path
handle_dir() {
	local GREP_DIR="$1"

	for src_file in "${GREP_DIR}"/*.cpp; do
		file_name=$(basename "${src_file}")
		prepare_sample "$file_name"
	done
	
	prepare_yaml
}
