#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


SAMPLES_DIR="$SCRIPT_DIR/samples"
EXAMPLES_DIR="$SCRIPT_DIR/../examples"


mkdir -p "$SAMPLES_DIR"


### output is non-deterministic
# ## printhtml sample
# TOOL_DIR="$EXAMPLES_DIR/ctrlflowgraph"
# "$TOOL_DIR"/generate.sh --ctrl_sample --printhtml
# 
# PAGE_PATH="$TOOL_DIR/build/html-ctrl_sample.cpp/@8.html"
# if [ -f "$PAGE_PATH" ]; then
# 	OUT_IMG_PATH="$SAMPLES_DIR/printhtml-page.png"
# 	chromium --headless --window-size=1920,1080 "file://$PAGE_PATH" --screenshot="$OUT_IMG_PATH"
# 	mogrify -trim "$OUT_IMG_PATH"
# 	convert -bordercolor \#EBEDEF -border 20 "$OUT_IMG_PATH" "$OUT_IMG_PATH"
# 	convert "$OUT_IMG_PATH" -strip "$OUT_IMG_PATH"
# 	exiftool -overwrite_original -all= "$OUT_IMG_PATH"
# fi


## inheritgraph sample
TOOL_DIR="$EXAMPLES_DIR/inheritgraph"
"$TOOL_DIR"/generate.sh --inherit_sample
cp "$TOOL_DIR/build/inherit_sample.cpp.svg" "$SAMPLES_DIR"


## memlayout sample
TOOL_DIR="$EXAMPLES_DIR/memlayout"
"$TOOL_DIR"/generate.sh --mem_sample
cp "$TOOL_DIR/build/mem_sample.cpp.svg" "$SAMPLES_DIR"


## ctrlflowgraph sample
TOOL_DIR="$EXAMPLES_DIR/ctrlflowgraph"
"$TOOL_DIR"/generate.sh --ctrl_sample
cp "$TOOL_DIR/build/ctrl_sample.cpp.puml.svg" "$SAMPLES_DIR"


# "$SCRIPT_DIR"/generate_small.sh
