#!/usr/bin/python3
#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

try:
    ## following import success only when file is directly executed from command line
    ## otherwise will throw exception when executing as parameter for "python -m"
    # pylint: disable=W0611
    import __init__
except ImportError:
    ## when import fails then it means that the script was executed indirectly
    ## in this case __init__ is already loaded
    pass

import sys
import argparse
import logging
import json

from gcclangrawparser import logger
from gcclangrawparser.langparser import parse_raw
from gcclangrawparser.io import write_file
from gcclangrawparser.langcontent import LangContent
from gcclangrawparser.printhtml import print_html, generate_big_graph, write_entry_tree


_LOGGER = logging.getLogger(__name__)


# =======================================================================


def process_parse(args):
    _LOGGER.info("parsing input file %s", args.rawfile)
    content: LangContent = parse_raw(args.rawfile, args.reducepaths)
    if content is None:
        raise RuntimeError(f"unable to parse {args.rawfile}")

    out_types_fields = args.outtypefields
    if out_types_fields:
        _LOGGER.info("dumping types dict")
        types_str = json.dumps(content.types_fields, indent=4)
        write_file(out_types_fields, types_str)

    if args.outtreetxt:
        _LOGGER.info("dumping nodes text representation to %s", args.outtreetxt)
        write_entry_tree(content, args.outtreetxt)

    if args.outbiggraph:
        _LOGGER.info("dumping nodes dot representation to %s", args.outbiggraph)
        generate_big_graph(content, args.outbiggraph)

    if args.outhtmldir:
        generate_page_graph = args.entrygraph
        use_vizjs = args.usevizjs
        jobs = args.jobs
        if jobs is not None:
            jobs = int(jobs)
        print_html(content, args.outhtmldir, generate_page_graph, use_vizjs, jobs)


# =======================================================================


def main():
    parser = argparse.ArgumentParser(
        prog="python3 -m gcclangrawparser.main",
        description="parse gcc/g++ raw internal tree data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=process_parse)
    parser.add_argument("-la", "--logall", action="store_true", help="Log all messages")
    parser.add_argument("--rawfile", action="store", required=True, default="", help="Path to raw file to analyze")
    parser.add_argument("--reducepaths", action="store", required=False, default="", help="Prefix to remove from paths")
    parser.add_argument(
        "--entrygraph", type=str2bool, nargs="?", const=True, default=True, help="Should generate graph for each entry?"
    )
    parser.add_argument(
        "--usevizjs",
        type=str2bool,
        nargs="?",
        const=True,
        default=True,
        help="Use viz.js standalone for graph rendering.",
    )
    parser.add_argument(
        "-j", "--jobs", action="store", required=False, default=None, help="Number to subprocesses to execute"
    )
    parser.add_argument(
        "--outtypefields", action="store", required=False, default="", help="Output path to types and fields "
    )
    parser.add_argument("--outtreetxt", action="store", required=False, default="", help="Output path to tree print")
    parser.add_argument("--outbiggraph", action="store", required=False, default="", help="Output path to big graph")
    parser.add_argument(
        "--outhtmldir", action="store", required=False, default="", help="Output directory for HTML representation"
    )

    ## =================================================

    args = parser.parse_args()

    if args.logall is True:
        logger.configure(logLevel=logging.DEBUG)
    else:
        logger.configure(logLevel=logging.INFO)

    if "func" not in args or args.func is None:
        ## no command given -- print help message
        parser.print_help()
        return 1

    return args.func(args)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    if v.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise argparse.ArgumentTypeError("Boolean value expected.")


if __name__ == "__main__":
    code = main()
    sys.exit(code)
