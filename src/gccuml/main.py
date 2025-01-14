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

from gccuml import logger
from gccuml.langparser import parse_raw
from gccuml.io import write_file
from gccuml.progressbar import disable_progressar
from gccuml.langcontent import LangContent, EntryTree
from gccuml.tool.tools import write_entry_tree, generate_big_graph
from gccuml.tool.printhtml import print_html
from gccuml.tool.inheritgraph import generate_inherit_graph
from gccuml.tool.memlayout import generate_memory_layout_graph
from gccuml.tool.ctrlflowgraph import generate_control_flow_graph


_LOGGER = logging.getLogger(__name__)


# =======================================================================


def process_tools(args):
    _LOGGER.info("parsing input file %s", args.rawfile)
    content: LangContent = parse_raw(args.rawfile, args.reducepaths)
    if content is None:
        raise RuntimeError(f"unable to parse {args.rawfile}")

    out_types_fields = args.outtypefields
    if out_types_fields:
        _LOGGER.info("dumping types dict")
        types_fields = content.get_types_fields()
        types_str = json.dumps(types_fields, indent=4)
        write_file(out_types_fields, types_str)

    include_internals = args.includeinternals
    entry_tree: EntryTree = EntryTree(content)
    entry_tree.generate_tree(include_internals=include_internals, depth_first=False)

    if args.outtreetxt:
        _LOGGER.info("dumping nodes text representation to %s", args.outtreetxt)
        write_entry_tree(entry_tree, args.outtreetxt)

    if args.outbiggraph:
        _LOGGER.info("dumping nodes dot representation to %s", args.outbiggraph)
        generate_big_graph(entry_tree, args.outbiggraph)


def process_printhtml(args):
    if not args.progressbar:
        disable_progressar()

    _LOGGER.info("parsing input file %s", args.rawfile)
    content: LangContent = parse_raw(args.rawfile, args.reducepaths)
    if content is None:
        raise RuntimeError(f"unable to parse {args.rawfile}")

    _LOGGER.info("generating entry tree")
    include_internals = args.includeinternals
    entry_tree: EntryTree = EntryTree(content)
    entry_tree.generate_tree(include_internals=include_internals, depth_first=False)

    if args.outhtmldir:
        generate_page_graph = args.genentrygraphs
        use_vizjs = args.usevizjs
        jobs = args.jobs
        if jobs is not None and jobs == "auto":
            jobs = None
        if jobs is not None:
            jobs = int(jobs)
        print_html(entry_tree, args.outhtmldir, generate_page_graph, use_vizjs, jobs)


def process_inheritgraph(args):
    _LOGGER.info("parsing input file %s", args.rawfile)
    content: LangContent = parse_raw(args.rawfile, args.reducepaths)
    if content is None:
        raise RuntimeError(f"unable to parse {args.rawfile}")
    generate_inherit_graph(content, args.outpath)


def process_memlayout(args):
    _LOGGER.info("parsing input file %s", args.rawfile)
    content: LangContent = parse_raw(args.rawfile, args.reducepaths)
    if content is None:
        raise RuntimeError(f"unable to parse {args.rawfile}")
    include_internals = args.includeinternals
    generate_memory_layout_graph(content, args.outpath, include_internals=include_internals, graphnote=args.graphnote)


def process_ctrlflowgraph(args):
    _LOGGER.info("parsing input file %s", args.rawfile)
    content: LangContent = parse_raw(args.rawfile, args.reducepaths)
    if content is None:
        raise RuntimeError(f"unable to parse {args.rawfile}")
    include_internals = args.includeinternals
    generate_control_flow_graph(content, args.outpath, include_internals=include_internals)


# =======================================================================


def main():
    parser = argparse.ArgumentParser(
        prog="python3 -m gccuml.main",
        description="generate UML-like diagrams based on gcc/g++ internal tree",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-la", "--logall", action="store_true", help="Log all messages")
    parser.add_argument("--listtools", action="store_true", help="List tools")
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers(help="one of tools", description="use one of tools", dest="tool", required=False)

    ## =================================================

    description = "various tools"
    subparser = subparsers.add_parser("tools", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparser.description = description
    subparser.set_defaults(func=process_tools)
    subparser.add_argument("--rawfile", action="store", required=True, default="", help="Path to raw file to analyze")
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default="", help="Prefix to remove from paths"
    )
    subparser.add_argument(
        "-ii",
        "--includeinternals",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Should include C++ internals?",
    )
    subparser.add_argument(
        "--outtypefields", action="store", required=False, default="", help="Output path to types and fields"
    )
    subparser.add_argument("--outtreetxt", action="store", required=False, default="", help="Output path to tree print")
    subparser.add_argument("--outbiggraph", action="store", required=False, default="", help="Output path to big graph")

    ## =================================================

    description = "generate static HTML for lang file"
    subparser = subparsers.add_parser(
        "printhtml", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_printhtml)
    subparser.add_argument("--rawfile", action="store", required=True, default="", help="Path to raw file to analyze")
    subparser.add_argument(
        "-j",
        "--jobs",
        action="store",
        required=False,
        default="auto",
        help="Number to subprocesses to execute. Auto means to spawn job per CPU core.",
    )
    subparser.add_argument(
        "--progressbar",
        type=str2bool,
        nargs="?",
        const=True,
        default=True,
        help="Show progress bar",
    )
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default="", help="Prefix to remove from paths"
    )
    subparser.add_argument(
        "--genentrygraphs",
        type=str2bool,
        nargs="?",
        const=True,
        default=True,
        help="Should generate graph for each entry?",
    )
    subparser.add_argument(
        "--usevizjs",
        type=str2bool,
        nargs="?",
        const=True,
        default=True,
        help="Use viz.js standalone for graph rendering.",
    )
    subparser.add_argument(
        "-ii",
        "--includeinternals",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Should include C++ internals?",
    )
    subparser.add_argument(
        "--outhtmldir", action="store", required=True, default="", help="Output directory for HTML representation"
    )

    ## =================================================

    description = "generate inheritance graph"
    subparser = subparsers.add_parser(
        "inheritgraph", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_inheritgraph)
    subparser.add_argument("--rawfile", action="store", required=True, default="", help="Path to raw file to analyze")
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default="", help="Prefix to remove from paths"
    )
    subparser.add_argument(
        "--outpath", action="store", required=True, default="", help="Output for for PUML representation"
    )

    ## =================================================

    description = "generate memory layout diagram"
    subparser = subparsers.add_parser(
        "memlayout", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_memlayout)
    subparser.add_argument("--rawfile", action="store", required=True, default="", help="Path to raw file to analyze")
    subparser.add_argument(
        "-ii",
        "--includeinternals",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Should include C++ internals?",
    )
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default="", help="Prefix to remove from paths"
    )
    subparser.add_argument("--graphnote", action="store", required=False, default="", help="Note to put on graph")
    subparser.add_argument(
        "--outpath", action="store", required=True, default="", help="Output path for DOT representation"
    )

    ## =================================================

    description = "generate control flow diagram"
    subparser = subparsers.add_parser(
        "ctrlflowgraph", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_ctrlflowgraph)
    subparser.add_argument("--rawfile", action="store", required=True, default="", help="Path to raw file to analyze")
    subparser.add_argument(
        "-ii",
        "--includeinternals",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Should include C++ internals?",
    )
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default="", help="Prefix to remove from paths"
    )
    subparser.add_argument(
        "--outpath", action="store", required=True, default="", help="Output path for DOT representation"
    )

    ## =================================================

    args = parser.parse_args()

    if args.listtools is True:
        tools_list = list(subparsers.choices.keys())
        print(", ".join(tools_list))
        return 0

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
    _LOGGER.info("exiting")
    sys.exit(code)
