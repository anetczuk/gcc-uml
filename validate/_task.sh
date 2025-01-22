#!/bin/bash
#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#


set -eu


## function to pop last line from file
popline()(
	LC_CTYPE=C 
	l=$(tail -n "${2:-1}" "$1"; echo t)
	l=${l%t}; truncate -s "-${#l}" "$1"
	#printf %s "$l"
)


## find proper files
## $1 - sources dir
## $2 - target file
##
find_sources() {
	local sources_dir="$1"
	local target_file_path="$2"

	## create file if does not exist
	touch "$target_file_path"
	if [ ! -s "$target_file_path" ]; then
		echo "finding source files"
	
		local NEWLINE=$'\n'
		c_files=$(find "$sources_dir" -type f -name "*.c")
		cpp_files=$(find "$sources_dir" -type f -name "*.cpp")
		src_files="${c_files}${NEWLINE}${cpp_files}"
		
		## shuffle is useful in case where in single directory are placed long-compiling files
		## but in other directories there are fast-compiling files, so
		src_files=$(echo "$src_files" | shuf)

		echo "$src_files" > "$target_file_path"
	fi
}
