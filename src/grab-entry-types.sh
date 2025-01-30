#!/bin/bash

set -eu

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
SCRIPT_NAME=$(basename "$(readlink -f "$0")")

GRAB_DIR="/tmp/grab"


mkdir -p "$GRAB_DIR"


## grab source code with tree definition
grab_file() {
	local repo_file="$1"
	local out_path="$2"

	if [ ! -f "${out_path}" ]; then
		wget "https://gcc.gnu.org/git/?p=gcc.git;a=blob_plain;f=${repo_file};hb=HEAD" -O "${out_path}"
	else
		echo "downloading ${repo_file} not needed"
	fi
}


## $1 - def file
## $2 - target file
append_file() {
	local def_file="$1"
	local target_file="$2"

	## extract all (including multiline) DEFTREECODE entries
	grep -zoP 'DEFTREECODE \([^\)]*?[^\)]*\)' "${def_file}" | tr '\n' ' ' | sed 's/\x0/\n/g' > /tmp/tree2

	## replace any "\" in file
	sed -i -e 's/\\//g' /tmp/tree2

	## convert DEFTREECODE to tuples
	cat /tmp/tree2 | awk -F ' ' '{ print( "(\"" substr($2,2,length($2)-2) "\",", $3, "\"" substr($4, 1, length($4)-1) "\",", $5) }' > /tmp/tree3

	cat /tmp/tree3 | while read -r line; do 
	   echo "    ${line}," >> "$target_file"
	done
}


## ========================================


OUT_TREE_DEF_PATH="${GRAB_DIR}/tree.def"
grab_file "gcc/tree.def" "$OUT_TREE_DEF_PATH"

OUT_CPTREE_DEF_PATH="${GRAB_DIR}/cp-tree.def"
grab_file "gcc/cp/cp-tree.def" "$OUT_CPTREE_DEF_PATH"


## convert to Python list
OUT_PATH="${SCRIPT_DIR}/gccuml/langentrylist.py"

cat > "$OUT_PATH" <<EOL
##
## File automatically generated using $SCRIPT_NAME script
##
## Source files taken from GCC compiler project to generate this file are:
##	  gcc/tree.def
##	  gcc/cp/cp-tree.def
##


##
## list of entries
## fields: symbol, name (used in dump-lang-raw), tree code class, number of argument-words
##
## tree code class meaning (taken from gcc/tree-core.h):
##     tcc_exceptional  -- An exceptional code (fits no category)
##     tcc_constant     -- A constant.
##     tcc_type         -- A type object code.
##     tcc_declaration  -- A declaration (also serving as variable refs).
##     tcc_reference    -- A reference to storage.
##     tcc_comparison   -- A comparison expression.
##     tcc_unary        -- A unary arithmetic expression.
##     tcc_binary       -- A binary arithmetic expression.
##     tcc_statement    -- A statement expression, which have side effects, but usually no interesting value.
##     tcc_vl_exp       -- A function call or other expression with a variable-length operand vector.
##     tcc_expression   -- Any other expression.
##
ENTRY_DEF_LIST = [
EOL


echo "    ## gcc/tree.def" >> "$OUT_PATH"
append_file "$OUT_TREE_DEF_PATH" "$OUT_PATH"

echo "" >> "$OUT_PATH"
echo "    ## gcc/cp/cp-tree.def" >> "$OUT_PATH"
append_file "$OUT_CPTREE_DEF_PATH" "$OUT_PATH"


cat >> "$OUT_PATH" <<EOL
]
EOL

echo "generated file: $OUT_PATH"
