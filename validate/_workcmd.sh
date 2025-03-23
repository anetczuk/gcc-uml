#!/bin/bash
#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#


set -eu


## $1 - lang file to check
## $2 - output directory
worker_printhtml() {
    local input_file="$1"
    local output_dir="$2"

    local cmd_log_level="WARNING"
    if [[ -v LOG_LEVEL ]]; then
        cmd_log_level="$LOG_LEVEL"
    fi

# 	"$PROJECT_COMMAND" -la \
    "$PROJECT_COMMAND" --loglevel "$cmd_log_level" \
                       --exitloglevel WARNING \
                       printhtml \
                       --rawfile "$input_file" \
                       --outpath "$output_dir/testhtml" \
                       -j 1 \
                       --progressbar F
}
export -f worker_printhtml


## $1 - lang file to check
## $2 - output directory
worker_memlayout() {
    local input_file="$1"
    local output_dir="$2"

    local cmd_log_level="WARNING"
    if [[ -v LOG_LEVEL ]]; then
        cmd_log_level="$LOG_LEVEL"
    fi

# 	"$PROJECT_COMMAND" -la \
    "$PROJECT_COMMAND" --loglevel "$cmd_log_level" \
                       --exitloglevel ERROR \
                       memlayout \
                       --rawfile "$input_file" \
                       --outpath "$output_dir/test.puml" \
                       -ii
}
export -f worker_memlayout


## $1 - lang file to check
## $2 - output directory
worker_inheritgraph() {
    local input_file="$1"
    local output_dir="$2"

    local cmd_log_level="WARNING"
    if [[ -v LOG_LEVEL ]]; then
        cmd_log_level="$LOG_LEVEL"
    fi

# 	"$PROJECT_COMMAND" -la \
    "$PROJECT_COMMAND" --loglevel "$cmd_log_level" \
                       --exitloglevel ERROR \
                       inheritgraph \
                       --rawfile "$input_file" \
                       --outpath "$output_dir/test.puml"
}
export -f worker_inheritgraph


## $1 - lang file to check
## $2 - output directory
worker_ctrlflowgraph() {
    local input_file="$1"
    local output_dir="$2"

    local cmd_log_level="WARNING"
    if [[ -v LOG_LEVEL ]]; then
        cmd_log_level="$LOG_LEVEL"
    fi

# 	"$PROJECT_COMMAND" -la \
    "$PROJECT_COMMAND" --loglevel "$cmd_log_level" \
                       --exitloglevel WARNING \
                       ctrlflowgraph \
                       --rawfile "$input_file" \
                       --outpath "$output_dir/test.puml"
}
export -f worker_ctrlflowgraph


if [[ "$*" == *"--printhtml"* ]]; then
    echo "using printhtml command"
    worker_command() {
        worker_printhtml "$@"
    }
elif [[ "$*" == *"--memlayout"* ]]; then
    echo "using memlayout command"
    worker_command() {
        worker_memlayout "$@"
    }
elif [[ "$*" == *"--inheritgraph"* ]]; then
    echo "using inheritgraph command"
    worker_command() {
        worker_inheritgraph "$@"
    }
elif [[ "$*" == *"--ctrlflowgraph"* ]]; then
    echo "using ctrlflowgraph command"
    worker_command() {
        worker_ctrlflowgraph "$@"
    }
else
    echo "no tool given, expected one of: --printhtml --inheritgraph --memlayout --ctrlflowgraph"
    exit 1
fi


export -f worker_command
