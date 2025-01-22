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


set -eu


## compile given file
## $1 - source file to check
## $2 - label
## 
compile_source() {
	local source_path="$1"
	local label="$2"

	local COMPILE_ERROR="0"
	timeout --foreground 20 "$GCC_COMMAND" -fdump-lang-raw -c "$source_path" 2> /dev/null || COMPILE_ERROR="1"
	if [ "$COMPILE_ERROR" -eq "1" ]; then
		echo "${label}: compilation error: $source_path"
		return 1
	else
		echo "${label}: file compiled:     $source_path"
		return 0
	fi
}


## read paths from file and work
## $1 - work dir
## $2 - work file
## $3 - results file
##
process_work_compile() {
	local work_dir="$1"
	local work_file="$2"
	local results_file="$3"

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
	 	compile_source "$srcfile" "$label" || WORK_ERROR="1"
	
		if [ "$WORK_ERROR" -eq "0" ]; then
			echo "$srcfile" >> "$results_file"
		fi

	 	popd > /dev/null

	 	popline "$work_file"

	 	## removing temporary directory is safer than removing content from custom path
	 	rm -r "$tempdir"
	done
}


export -f popline
export -f compile_source
export -f process_work_compile


## run scan and check
## $1 - sources dir
## $2 - jobs number
## $3 - output file
##
run_scan() {
	local sources_root_dir="$1"
	local jobs_num="$2"
	local output_file_path="$3"
	
	local work_dir="$(pwd)"
	local progress_file_path="${work_dir}/sources-found.txt"
	
	local scan_parts_prefix="scan-part-"
	
	
	mkdir -p "$work_dir/tmp"
	
	cd "$work_dir"	


	scan_parts=$(ls "$scan_parts_prefix"* 2> /dev/null ) || true
	if [[ "$scan_parts" == "" ]]; then
		if [ -f "$output_file_path" ]; then
			echo "scan result already exists"
			echo "remove file $output_file_path to scan again"
			return
		fi
	fi
	
	
	find_sources "$sources_root_dir" "$progress_file_path"
	
	split_file "$progress_file_path" "$jobs_num" "$scan_parts_prefix" 
	
	
	scan_parts=$(ls "$scan_parts_prefix"*)
		
	run_in_parallel process_work_compile "$scan_parts" "$output_file_path"
	
	for item in $scan_parts; do
		rm "$item"
	done
}
