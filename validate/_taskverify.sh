#!/bin/bash
#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#


## following variables have to be defined
# GCC_COMMAND
# PROJECT_COMMAND


set -eu


## analyze given file
verify_source() {
	local source_path="$1"
	local label="$2"

	local COMPILE_ERROR="0"
	"$GCC_COMMAND" -fdump-lang-raw -c "$source_path" 2> /dev/null || COMPILE_ERROR="1"
	if [ "$COMPILE_ERROR" -eq "1" ]; then
		echo "${label}: compilation error: $source_path"
		return 0
	fi

	echo "${label}: processing: $source_path"

	local SOURCE_FILE_NAME="$(basename "$source_path")"
	local LANG_FILE_PATH="${SOURCE_FILE_NAME}.003l.raw"

	if [ ! -f "$LANG_FILE_PATH" ]; then
		echo "unable to find lang file: $LANG_FILE_PATH"
		return 0
	fi

# 	echo "processing raw file: $(realpath $LANG_FILE_PATH)"

	local out_dir="$(pwd)"

	local RUN_ERROR="0"

# # 	"$PROJECT_COMMAND" -la \
# 	"$PROJECT_COMMAND" --loglevel WARNING \
# 					   --exitloglevel ERROR \
# 					   memlayout \
# 				       --rawfile "$LANG_FILE_PATH" \
# 					   --outpath "$out_dir/test.puml" \
# 					   -ii \
# 					   || RUN_ERROR="1"
# 
# 	if [ "$RUN_ERROR" -eq "1" ]; then
# 		echo -e "\nerror while processing file: ${source_path}"
# 		return 1
# 	fi
# 
# 
# # 	"$PROJECT_COMMAND" -la \
# 	"$PROJECT_COMMAND" --loglevel WARNING \
# 					   --exitloglevel ERROR \
# 					   inheritgraph \
# 				       --rawfile "$LANG_FILE_PATH" \
# 					   --outpath "$out_dir/test.puml" \
# 					   || RUN_ERROR="1"
# 
# 	if [ "$RUN_ERROR" -eq "1" ]; then
# 		echo -e "\nerror while processing file: ${source_path}"
# 		return 1
# 	fi


# 	"$PROJECT_COMMAND" -la \
	"$PROJECT_COMMAND" --loglevel WARNING \
					   --exitloglevel ERROR \
					   ctrlflowgraph \
				       --rawfile "$LANG_FILE_PATH" \
					   --outpath "$out_dir/test.puml" \
					   || RUN_ERROR="1"


	if [ "$RUN_ERROR" -eq "1" ]; then
		echo -e "\nerror while processing file: ${source_path}"
		LANG_FULL_PATH="$(realpath "${LANG_FILE_PATH}")"
		echo "source lang file: ${LANG_FULL_PATH}"
		return 1
	fi
}


## read paths from file and work
## $1 - work dir
## $2 - work file
##
process_work_verify() {
	local work_dir="$1"
	local work_file="$2"

	echo "processing work dir: $work_dir"
	echo "processing work file: $work_file"

	local found_items_num=$(wc -l "$work_file" | awk '{ print $1 }')

	cd "$work_dir"

	local counter=0
	while true; do
		local srcfile=$(tail -1 "$work_file")
		if [[ "$srcfile" == "" ]];  then
			echo -e "\ncompleted"
			exit 0
		fi

		tempdir=$(mktemp -p tmp -d tmp.XXXXXXXXXX)
		pushd "$tempdir" > /dev/null
	
		counter=$((counter+1))
		local label="$counter of $found_items_num"
	
		local WORK_ERROR="0"
	 	verify_source "$srcfile" "$label" || WORK_ERROR="1"
	
		if [ "$WORK_ERROR" -ne "0" ]; then
			#echo "$srcfile" >> "$OUTPUT_FILE_PATH"
			exit 1
		fi

	 	popd > /dev/null

	 	popline "$work_file"

	 	## removing temporary directory is safer than removing content from custom path
	 	rm -r "$tempdir"
	done
}


export -f popline
export -f verify_source
export -f process_work_verify


## run verify
## $1 - input file
## $2 - jobs number
## $3 - output file
##
run_verify() {
	local progress_file_path="$1"
	local jobs_num="$2"
	local output_file_path="$3"
	
	local work_dir="$(pwd)"
	
	local scan_parts_prefix="verify-part-"


	mkdir -p "$work_dir/tmp"
	
	cd "$work_dir"	
	
	
	split_file "$progress_file_path" "$jobs_num" "$scan_parts_prefix" 


	scan_parts=$(ls "$scan_parts_prefix"*)

	run_in_parallel process_work_verify "$jobs_num" "$scan_parts" "$output_file_path"
	
	for item in $scan_parts; do
		rm "$item"
	done

	echo -e "\nall completed"
}
