#!/bin/bash

set -eu

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
SCRIPT_NAME=$(basename "$(readlink -f "$0")")


## grab source code with tree definition
OUT_DEF_PATH="/tmp/tree.def"
if [ ! -f "${OUT_DEF_PATH}" ]; then
	wget "https://gcc.gnu.org/git/?p=gcc.git;a=blob_plain;f=gcc/tree.def;hb=HEAD" -O "${OUT_DEF_PATH}"
else
	echo "downloading tree.def not needed"
fi


## extract all (including multiline) DEFTREECODE entries
grep -zoP 'DEFTREECODE \([^\)]*?[^\)]*\)' "${OUT_DEF_PATH}" | tr '\n' ' ' | sed 's/\x0/\n/g' > /tmp/tree2


## convert DEFTREECODE to tuples
cat /tmp/tree2 | awk -F ' ' '{ print( "(\"" substr($2,2,length($2)-2) "\",", $3, "\"" substr($4, 1, length($4)-1) "\",", $5) }' > /tmp/tree3


## convert to Python list
OUT_PATH="${SCRIPT_DIR}/gccuml/langentrylist.py"

cat > "$OUT_PATH" <<EOL
##
## File automatically generated using $SCRIPT_NAME script
##
## Source file taken to generate this file is gcc/tree.def
## from GCC compiler project.
##


## list of entries defined in gcc/tree.def
## fields: symbol, name (used in dump-lang-raw), type, number of argument-words 
ENTRY_DEF_LIST = [
EOL

cat /tmp/tree3 | while read line; do 
   echo "    ${line}," >> "$OUT_PATH"
done

cat >> "$OUT_PATH" <<EOL
]
EOL

echo "generated file: $OUT_PATH"
