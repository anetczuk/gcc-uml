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
import os
import argparse
import logging

from gccuml import logger
from gccuml.configyaml import (
    read_config,
    Config,
    TOP_LEVEL_ITEMS,
    DIAGRAMS_LEVEL_ITEMS,
    get_base_directory,
    find_input_files,
)
from gccuml.tool.tools import process_tools_config
from gccuml.tool.printhtml import print_html_config
from gccuml.tool.inheritgraph import generate_inherit_graph_config
from gccuml.tool.memlayout import generate_memory_layout_graph_config
from gccuml.tool.ctrlflowgraph import generate_control_flow_graph_config, get_engine_file_extension


if __name__ == "__main__":
    _LOGGER = logging.getLogger("gccuml.main")
else:
    _LOGGER = logging.getLogger(__name__)


# =======================================================================


def process_config(args):
    config_path = args.path
    _LOGGER.info("parsing config file %s", config_path)
    config: Config = read_config(config_path)
    if config is None:
        raise RuntimeError(f"unable to parse {config_path}")

    for top_item in config.params:
        if top_item not in TOP_LEVEL_ITEMS:
            _LOGGER.warning("unknown top level config item: %s", top_item)

    ## handled
    # output_directory
    # debug_mode

    ## not applicable:
    # add_compile_flags
    # remove_compile_flags
    # user_data
    # query_driver
    # compilation_database_dir

    output_directory = config.get("output_directory")
    debug_mode = config.get("debug_mode")

    diagrams_dict = config.get("diagrams")
    if diagrams_dict is None:
        raise RuntimeError("unable to find 'diagrams' item")

    for diagram_name, diagram_config in diagrams_dict.items():
        if diagram_config is None:
            _LOGGER.warning("invalid config diagram entry: %s", diagram_name)
            continue

        for diag_item in diagram_config:
            if diag_item not in DIAGRAMS_LEVEL_ITEMS:
                _LOGGER.warning("unknown diagram level config item: %s", diag_item)


        # type : class, sequence, package, include
        # include_relations_also_as_members
        # generate_method_arguments
        # generate_concept_requirements
        # using_namespace
        # generate_packages
        # package_type
        # include
        # exclude

        ## handled
        # relative_to
        # glob

        ## not applicable:
        # layout
        # plantuml
        # mermaid
        # graphml

        diagram_type = diagram_config.get("type")

        diagram_relative_to = diagram_config.get("relative_to")
        diagram_base_directory = get_base_directory(config_path, diagram_relative_to)
        diagram_output_directory = None
        if output_directory:
            diagram_output_directory = get_base_directory(output_directory, diagram_relative_to)
        else:
            diagram_output_directory = get_base_directory(config_path, diagram_relative_to)

        diagram_glob_list = diagram_config.get("glob")
        input_files = find_input_files(diagram_glob_list, diagram_base_directory)
        if not input_files:
            _LOGGER.warning("unable to find input files for diagram '%s'", diagram_name)
            continue

        config_dict = diagram_config.copy()
        config_dict["debug_mode"] = debug_mode
        config_dict["inputfiles"] = input_files

        if diagram_type == "printhtml":
            config_dict["outpath"] = os.path.join(diagram_output_directory, f"{diagram_name}")
            print_html_config(config_dict)
            continue

        if diagram_type == "inheritgraph":
            config_dict["outpath"] = os.path.join(diagram_output_directory, f"{diagram_name}.puml")
            generate_inherit_graph_config(config_dict)
            continue

        if diagram_type == "memlayout":
            config_dict["outpath"] = os.path.join(diagram_output_directory, f"{diagram_name}.dot")
            generate_memory_layout_graph_config(config_dict)
            continue

        if diagram_type == "ctrlflowgraph":
            diagram_engine = config_dict.get("engine", "dot")
            out_extension = get_engine_file_extension(diagram_engine)
            config_dict["outpath"] = os.path.join(diagram_output_directory, f"{diagram_name}.{out_extension}")
            generate_control_flow_graph_config(config_dict)
            continue

        if diagram_type == "tools":
            process_tools_config(config_dict)
            continue

        raise RuntimeError(f"unknown diagram '{diagram_type}'")


def process_printhtml(args):
    config_dict = {
        "inputfiles": [args.rawfile],
        "jobs": args.jobs,
        "progressbar": args.progressbar,
        "reducepaths": args.reducepaths,
        "notransform": args.notransform,
        "genentrygraphs": args.genentrygraphs,
        "usevizjs": args.usevizjs,
        "includeinternals": args.includeinternals,
        "outpath": args.outpath,
    }
    print_html_config(config_dict)


def process_inheritgraph(args):
    config_dict = {
        "inputfiles": [args.rawfile],
        "reducepaths": args.reducepaths,
        "outpath": args.outpath,
    }
    generate_inherit_graph_config(config_dict)


def process_memlayout(args):
    config_dict = {
        "inputfiles": [args.rawfile],
        "reducepaths": args.reducepaths,
        "includeinternals": args.includeinternals,
        "graphnote": args.graphnote,
        "outpath": args.outpath,
    }
    generate_memory_layout_graph_config(config_dict)


def process_ctrlflowgraph(args):
    config_dict = {
        "inputfiles": [args.rawfile],
        "reducepaths": args.reducepaths,
        "includeinternals": args.includeinternals,
        "engine": args.engine,
        "outpath": args.outpath,
    }
    generate_control_flow_graph_config(config_dict)


def process_tools(args):
    config_dict = {
        "inputfiles": [args.rawfile],
        "reducepaths": args.reducepaths,
        "outtypefields": args.outtypefields,
        "outtreetxt": args.outtreetxt,
        "outbiggraph": args.outbiggraph,
        "includeinternals": args.includeinternals,
    }
    process_tools_config(config_dict)


# =======================================================================


def main():
    parser = argparse.ArgumentParser(
        prog="python3 -m gccuml.main",
        description="generate UML-like diagrams based on gcc/g++ internal tree",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--loglevel", action="store", default=None, help="Set log level")
    parser.add_argument("-la", "--logall", action="store_true", help="Log all messages")
    parser.add_argument("--exitloglevel", action="store", default=None, help="Set exit log level")
    parser.add_argument("--listtools", action="store_true", help="List tools")
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers(help="one of tools", description="use one of tools", dest="tool", required=False)

    ## =================================================

    description = "read configuration file"
    subparser = subparsers.add_parser(
        "config", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_config)
    subparser.add_argument(
        "--path",
        action="store",
        required=True,
        default=None,
        help="Path to configuration YAML file",
    )

    ## =================================================

    description = "generate static HTML for internal tree file"
    subparser = subparsers.add_parser(
        "printhtml", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_printhtml)
    subparser.add_argument(
        "--rawfile",
        action="store",
        required=True,
        default=None,
        help="Path to internal tree file (.003l.raw) to analyze",
    )
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
        "--reducepaths", action="store", required=False, default=None, help="Prefix to remove from paths inside tree"
    )
    subparser.add_argument(
        "--notransform",
        type=str2bool,
        nargs="?",
        const=False,
        default=False,
        help="Should prevent transforming internal tree before printing?",
    )
    subparser.add_argument(
        "--genentrygraphs",
        type=str2bool,
        nargs="?",
        const=True,
        default=True,
        help="Should graph be generated for each entry?",
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
        help="Should include compiler internals?",
    )
    subparser.add_argument(
        "--outpath", action="store", required=True, default=None, help="Output directory of HTML representation"
    )

    ## =================================================

    description = "generate inheritance graph"
    subparser = subparsers.add_parser(
        "inheritgraph", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_inheritgraph)
    subparser.add_argument(
        "--rawfile",
        action="store",
        required=True,
        default=None,
        help="Path to internal tree file (.003l.raw) to analyze",
    )
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default=None, help="Prefix to remove from paths inside tree"
    )
    subparser.add_argument(
        "--outpath", action="store", required=True, default=None, help="Output path of PlantUML representation"
    )

    ## =================================================

    description = "generate memory layout diagram"
    subparser = subparsers.add_parser(
        "memlayout", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_memlayout)
    subparser.add_argument("--rawfile", action="store", required=True, default=None, help="Path to raw file to analyze")
    subparser.add_argument(
        "-ii",
        "--includeinternals",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Should include compiler internals?",
    )
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default=None, help="Prefix to remove from paths inside tree"
    )
    subparser.add_argument("--graphnote", action="store", required=False, default=None, help="Note to put on graph")
    subparser.add_argument(
        "--outpath", action="store", required=True, default=None, help="Output path of DOT representation"
    )

    ## =================================================

    description = "generate control flow diagram"
    subparser = subparsers.add_parser(
        "ctrlflowgraph", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparser.description = description
    subparser.set_defaults(func=process_ctrlflowgraph)
    subparser.add_argument(
        "--rawfile",
        action="store",
        required=True,
        default=None,
        help="Path to internal tree file (.003l.raw) to analyze",
    )
    subparser.add_argument(
        "-ii",
        "--includeinternals",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Should include compiler internals?",
    )
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default=None, help="Prefix to remove from paths inside tree"
    )
    subparser.add_argument(
        "--engine", action="store", required=False, default="dot", help="Diagram engine: dot, plantuml"
    )
    subparser.add_argument(
        "--outpath", action="store", required=True, default=None, help="Output path for DOT representation"
    )

    ## =================================================

    description = "various tools"
    subparser = subparsers.add_parser("tools", help=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparser.description = description
    subparser.set_defaults(func=process_tools)
    subparser.add_argument(
        "--rawfile",
        action="store",
        required=True,
        default=None,
        help="Path to internal tree file (.003l.raw)e to analyze",
    )
    subparser.add_argument(
        "--reducepaths", action="store", required=False, default=None, help="Prefix to remove from paths inside tree"
    )
    subparser.add_argument(
        "-ii",
        "--includeinternals",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Should include compiler internals?",
    )
    subparser.add_argument(
        "--outtypefields", action="store", required=False, default=None, help="Output path to types and fields"
    )
    subparser.add_argument(
        "--outtreetxt", action="store", required=False, default=None, help="Output path to tree print"
    )
    subparser.add_argument(
        "--outbiggraph", action="store", required=False, default=None, help="Output path to big graph"
    )

    ## =================================================

    args = parser.parse_args()

    if args.listtools is True:
        tools_list = list(subparsers.choices.keys())
        print(", ".join(tools_list))
        return 0

    if args.logall is True:
        logger.configure(logLevel=logging.DEBUG)
    elif args.loglevel is not None:
        loglevel_map = logging.getLevelNamesMapping()
        loglevel = loglevel_map.get(args.loglevel)
        if loglevel is not None:
            logger.configure(logLevel=loglevel)
        else:
            logger.configure(logLevel=logging.INFO)
            _LOGGER.info("loglevel not found - invalid loglevel name: %s", args.loglevel)
    else:
        # default log level
        logger.configure(logLevel=logging.INFO)

    if args.exitloglevel:
        loglevel_map = logging.getLevelNamesMapping()
        loglevel = loglevel_map.get(args.exitloglevel)
        if loglevel is not None:
            logger.add_exit_handler(loglevel)
        else:
            _LOGGER.info("loglevel not found - invalid loglevel name: %s", args.exitloglevel)

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
