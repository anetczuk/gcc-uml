#!/bin/bash
#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#


set -eu


## split single file to multiple files
## $1 - file to split
## $2 - number of parts
## $3 - split prefix
##
split_file() {
	local split_file_path="$1"
	local parts_num="$2"
	local split_prefix="$3"

	scan_parts=$(ls "$split_prefix"* 2> /dev/null ) || true
	
	if [[ "$scan_parts" == "" ]]; then
		echo "splitting progress file into $parts_num parts"
	
		found_items_num=$(wc -l "$split_file_path" | awk '{ print $1 }')
		params=""
		if [[ $parts_num -gt 1 ]]; then
			line_index=0
			for ind in $(seq 2 "$parts_num"); do
				line_index=$(( (ind - 1) * found_items_num / parts_num ))
			    params="$params $line_index"
			done
			# shellcheck disable=SC2086
			csplit -f "$split_prefix" "$split_file_path" $params > /dev/null
		else
			params=$((found_items_num + 1))
			cp "$split_file_path" "${split_prefix}00"
		fi
	else
		echo "split files found - countinue"
	fi
}


## parallel worker
## $1 - function to call
## $2 - work directory
## $3 - work file
## $4 - result file
##
parallel_work() {
	set -eu
	"$@"
}
export -f parallel_work


## run in parallel
## $1 - worker function to call
## $2 - maximal number of workers
## $3 - list of files to pass to worker
## $4 - results file
##
run_in_parallel() {
	local worker_function="$1"
	local jobs_num="$2"
	local scan_parts="$3"
	local results_file="$4"

	time parallel -j "$jobs_num" --halt-on-error 2 -u ::: parallel_work ::: "$worker_function" ::: "$(pwd)" ::: "$scan_parts" ::: "$results_file"
}
