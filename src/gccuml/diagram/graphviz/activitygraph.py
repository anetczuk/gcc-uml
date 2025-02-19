# Copyright (c) 2025, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
from typing import Dict, List, Any
import graphviz

from showgraph.io import write_file

from gccuml.diagram import activitydata
from gccuml.diagram.activitydata import StatementType


_LOGGER = logging.getLogger(__name__)


## ===========================================================


class GraphGenerator:

    def __init__(self):
        self.item_id = -1

    def next_id(self) -> str:
        self.item_id += 1
        return f"item_{self.item_id}"

    def generate_data(self, dotgraph: graphviz.Digraph, data: Any) -> List[str]:
        if isinstance(data, str):
            node_id = self.next_id()
            dotgraph.node(node_id, label=data)
            return [node_id]

        if isinstance(data, list):
            return self.generate_list(dotgraph, data)

        if isinstance(data, activitydata.SwitchStatement):
            label = rf"switch:\l{data.name}"
            node_id = self.next_id()
            subgraph_attr = {"label": label}
            subgraph_mgr = dotgraph.subgraph(name=f"cluster_{node_id}")
            # subgraph_mgr = dotgraph.subgraph(name="cluster_xxx", graph_attr=subgraph_attr)
            with subgraph_mgr as subgraph:
                subgraph.attr("graph", subgraph_attr)
                return self.generate_switch(subgraph, data)
            return self.generate_statement(dotgraph, data)

        if isinstance(data, activitydata.TypedStatement):
            return self.generate_statement(dotgraph, data)

        if isinstance(data, activitydata.Statement):
            stat = activitydata.TypedStatement(data.name)
            stat.color = data.color
            return self.generate_statement(dotgraph, stat)

        if isinstance(data, activitydata.StatementList):
            return self.generate_list(dotgraph, data.items)

        if isinstance(data, activitydata.LabeledCard):
            return self.generate_cluster(dotgraph, data.label, data.subitems, data.has_return)

        if isinstance(data, activitydata.LabeledGroup):
            return self.generate_cluster(dotgraph, data.label, data.subitems)

        raise RuntimeError(f"unhandled data: {type(data)}")

    def generate_list(self, dotgraph: graphviz.Digraph, data: List[activitydata.ActivityData]) -> List[str]:
        ret_list: List[str] = []
        for item in data:
            sub_list = self.generate_data(dotgraph, item)
            if ret_list and sub_list:
                last_node_id = ret_list[-1]
                # if not last_node_id:
                #     raise RuntimeError(f"invalid case for item: {data}")
                next_node_id = sub_list[0]
                if next_node_id:
                    if last_node_id:
                        dotgraph.edge(last_node_id, next_node_id)
                    else:
                        last_node_id = get_non_none_last_element(ret_list)
                        self.add_edge_hidden(dotgraph, last_node_id, next_node_id)
            ret_list.extend(sub_list)
        return ret_list

    def generate_statement(self, dotgraph: graphviz.Digraph, data: activitydata.TypedStatement) -> List[str]:
        if data.type == StatementType.UNSUPPORTED:
            node_id = self.next_id()
            node_label = f"{data.name}\nnot supported"
            dotgraph.node(node_id, label=node_label, fillcolor=activitydata.UNSUPPORTED_COLOR)
            return [node_id]

        if data.type == StatementType.NODE:
            node_id = self.next_id()
            dotgraph.node(node_id, label=data.name, fillcolor=data.color)
            return [node_id]

        if data.type == StatementType.STOP:
            node_id = None
            if data.name:
                node_id = self.next_id()
                dotgraph.node(node_id, label=data.name, fillcolor=activitydata.LAST_NODE_COLOR)
            stop_node_id = self.next_id()
            dotgraph.node(
                stop_node_id,
                shape="doublecircle",
                fillcolor="black",
                label="",
                size="0.1",
                fixedsize="true",
                width="0.12",
                height="0.12",
            )
            if node_id:
                dotgraph.edge(node_id, stop_node_id)
                return [node_id, stop_node_id, None]
            return [stop_node_id, None]

        if data.type == StatementType.IF:
            return self.generate_if(dotgraph, data)

        raise RuntimeError(f"unhandled statement type: {data.type}")

    def generate_if(self, dotgraph: graphviz.Digraph, ifData: activitydata.TypedStatement) -> List[str]:
        items_len = len(ifData.items)
        if items_len != 2:
            raise RuntimeError(f"invalid IF node: required 2 items, got {items_len}")
        true_branch = ifData.items[0]
        false_branch = ifData.items[1]

        if_node_id = self.next_id()
        self.add_node_if(dotgraph, if_node_id, ifData.name, ifData.color)

        true_list = self.generate_list(dotgraph, true_branch)
        false_list = self.generate_list(dotgraph, false_branch)

        end_if_node_id = self.next_id()
        end_if_used = False

        true_last = None
        if true_list:
            true_first = true_list[0]
            dotgraph.edge(if_node_id, true_first, label="true")
            true_last = true_list[-1]
            if true_last:
                dotgraph.edge(true_last, end_if_node_id)
                end_if_used = True
        else:
            dotgraph.edge(if_node_id, end_if_node_id, label="true")
            end_if_used = True

        false_last = None
        if false_list:
            false_first = false_list[0]
            dotgraph.edge(if_node_id, false_first, label="false")
            false_last = false_list[-1]
            if false_last:
                dotgraph.edge(false_last, end_if_node_id)
                end_if_used = True
        else:
            dotgraph.edge(if_node_id, end_if_node_id, label="false")
            end_if_used = True

        if end_if_used:
            self.add_node_join(dotgraph, end_if_node_id, ifData.color)
            return [if_node_id, end_if_node_id]

        return [if_node_id, None]

    def generate_switch(self, dotgraph: graphviz.Digraph, data: activitydata.SwitchStatement) -> List[str]:
        ret_list = []

        end_switch_node_id = self.next_id()
        end_switch_node_used = False

        prev_case_node_id = None

        case_node_id_dict = {}

        ## add "No" path
        for case_index, case_item in enumerate(data.items):
            case_value = case_item[0]
            case_node_id = self.next_id()
            case_node_id_dict[case_index] = case_node_id
            case_label = case_value
            if case_value is None:
                ## default case
                case_label = "default:"
            self.add_node_if(dotgraph, case_node_id, case_label)
            ret_list.append(case_node_id)

            if prev_case_node_id:
                dotgraph.edge(prev_case_node_id, case_node_id)
            prev_case_node_id = case_node_id

        ## add "Yes" path
        for case_index, case_item in enumerate(data.items):
            ## case_value -- None -- default case
            case_value = case_item[0]
            case_fallthrough = case_item[1]
            case_statements = case_item[2]

            case_node_id = case_node_id_dict[case_index]

            case_ret_list = self.generate_list(dotgraph, case_statements)
            if case_ret_list:
                first_node_id = case_ret_list[0]
                edge_label = None
                if case_value is not None:
                    edge_label = "yes"
                dotgraph.edge(case_node_id, first_node_id, label=edge_label)
                last_node_id = case_ret_list[-1]
                if last_node_id is not None:
                    if not case_fallthrough:
                        dotgraph.edge(last_node_id, end_switch_node_id)
                        end_switch_node_used = True
                    else:
                        prev_case_node_id = last_node_id
                        next_case_node_id = case_node_id_dict.get(case_index + 1)
                        if next_case_node_id:
                            dotgraph.edge(last_node_id, next_case_node_id)
                        else:
                            # last case - to switch end
                            dotgraph.edge(last_node_id, end_switch_node_id)
                            end_switch_node_used = True
                # else:
                #     # return inside case
                #     recent_node_id = get_non_none_last_element(case_ret_list)
                #     self.add_edge_hidden(dotgraph, recent_node_id, end_switch_node_id)
                #     end_switch_node_used = True
            else:
                ## no items -- fallthrough
                if not case_fallthrough:
                    ## break used
                    dotgraph.edge(case_node_id, end_switch_node_id, label="yes")
                    end_switch_node_used = True
                ## else do nothing

            prev_case_node_id = case_node_id

        if end_switch_node_used:
            self.add_node_join(dotgraph, end_switch_node_id)
            ret_list.append(end_switch_node_id)
        else:
            ret_list.append(None)

        ############

        # end_switch_node_id = self.next_id()
        # end_switch_node_used = False
        #
        # prev_case_node_id = None
        # prev_is_default = False
        #
        # for case_item in data.items:
        #     ## case_value -- None -- default case
        #     case_value = case_item[0]
        #     case_fallthrough = case_item[1]
        #     case_statements = case_item[2]
        #
        #     prev_is_default = False
        #
        #     case_node_id = self.next_id()
        #     case_label = case_value
        #     if case_value is None:
        #         ## default case
        #         prev_is_default = True
        #         case_label = "default:"
        #
        #     self.add_node_if(dotgraph, case_node_id, case_label)
        #     ret_list.append(case_node_id)
        #
        #     if prev_case_node_id:
        #         dotgraph.edge(prev_case_node_id, case_node_id)
        #     prev_case_node_id = case_node_id
        #
        #     # if not case_statements:
        #     #     ## empty case --fallthrough
        #     #     continue
        #
        #     case_ret_list = self.generate_list(dotgraph, case_statements)
        #     if case_ret_list:
        #         first_node_id = case_ret_list[0]
        #         edge_label = None
        #         if case_value is not None:
        #             edge_label = "yes"
        #         dotgraph.edge(case_node_id, first_node_id, label=edge_label)
        #         last_node_id = case_ret_list[-1]
        #         if last_node_id is not None:
        #             if case_fallthrough:
        #                 prev_case_node_id = last_node_id
        #             else:
        #                 dotgraph.edge(last_node_id, end_switch_node_id)
        #                 end_switch_node_used = True
        #     else:
        #         ## no items -- fallthrough
        #         pass
        #
        # if prev_is_default is False:
        #     if prev_case_node_id is not None:
        #         dotgraph.edge(prev_case_node_id, end_switch_node_id)
        #         end_switch_node_used = True
        #
        # if end_switch_node_used:
        #     self.add_node_join(dotgraph, end_switch_node_id)
        #     ret_list.append(end_switch_node_id)
        # else:
        #     ret_list.append(None)

        return ret_list

    def generate_cluster(self, dotgraph: graphviz.Digraph, label, subitems, has_return=False) -> List[str]:
        node_id = self.next_id()
        subgraph_attr = {"label": label}
        subgraph_mgr = dotgraph.subgraph(name=f"cluster_{node_id}")
        # subgraph_mgr = dotgraph.subgraph(name="cluster_xxx", graph_attr=subgraph_attr)
        with subgraph_mgr as subgraph:
            subgraph.attr("graph", subgraph_attr)
            ret_list = self.generate_list(subgraph, subitems)
            if has_return:
                ret_list.append(None)
            return ret_list

    def add_node_if(self, dotgraph: graphviz.Digraph, node_id, label=None, fillcolor=None):
        dotgraph.node(node_id, style="filled", shape="diamond", label=label, fillcolor=fillcolor)

    def add_node_join(self, dotgraph: graphviz.Digraph, node_id, fillcolor=None):
        dotgraph.node(
            node_id, label="", width="0.2", height="0.2", style="filled", shape="diamond", fillcolor=fillcolor
        )

    def add_edge_hidden(self, dotgraph: graphviz.Digraph, from_node_id, to_node_id):
        dotgraph.edge(from_node_id, to_node_id, style="invis")


def get_non_none_last_element(data_list):
    last_present_value = next(x for x in reversed(data_list) if x is not None)
    return last_present_value


## ===========================================================


# def convert_tuple(data_tuple):
#     ret_list = convert_list(data_tuple)
#     return tuple(ret_list)
#
#
# def convert_list(data_list: List[activitydata.ActivityData]) -> List[ActivityItem]:
#     ret_list = []
#     for data in data_list:
#         converted = convert_data(data)
#         ret_list.append(converted)
#     return ret_list
#
#
# def convert_dict(data_dict: Dict[str, activitydata.ActivityData]) -> Dict[str, ActivityItem]:
#     ret_dict = {}
#     for key, data in data_dict.items():
#         converted = convert_data(data)
#         ret_dict[key] = converted
#     return ret_dict


## ===========================================================


## Generator for DOT activity diagrams
class ActivityGraphGenerator:

    def __init__(self, data_dict: Dict[str, activitydata.ActivityData] = None):
        self.data = data_dict
        if self.data is None:
            self.data = {}
        self.dotgraph: graphviz.Digraph = None

    def generate(self, out_path):
        self.dotgraph = graphviz.Digraph()

        if not self.data:
            ## empty data
            _LOGGER.info("writing output to file %s", out_path)
            self.dotgraph.render(out_path)
            return

        # generate
        graph_attr = {"ranksep": "0.35", "fontname": "SansSerif,sans-serif", "nojustify": "true", "labeljust": "l"}
        self.dotgraph.attr(None, graph_attr)

        node_attr = {
            "shape": "box",
            "style": "filled, rounded",
            "fillcolor": activitydata.NODE_COLOR,
            "fontsize": "10",
            "fontname": "SansSerif,sans-serif",
            "height": "0.35",
        }
        self.dotgraph.attr("node", node_attr)

        generator = GraphGenerator()

        items_list = list(self.data.values())
        generator.generate_data(self.dotgraph, items_list)
        content = self.dotgraph.source

        _LOGGER.info("writing output to file %s", out_path)
        # self.dotgraph.render(out_path, format="gv")
        write_file(out_path, content)

        # graphviz.render("dot", format="svg", filepath=out_path, outfile=f"{out_path}.svg")

    def generate_svg(self, out_path):
        temporary_dot = "/tmp/graph.dot"
        self.generate(temporary_dot)
        graphviz.render("dot", format="svg", filepath=temporary_dot, outfile=out_path)
