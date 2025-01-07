#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest

from gcclangrawparser.langcontent import LangContent, get_entry_tree, EntryTreeDepthFirstTraversal


class GetEntryTeeTest(unittest.TestCase):

    def test_get_entry_tree_recursive(self):
        data_dict = {
            "@1": ("@1", "void_type", [("name", "@9"), ("algn", "8")]),
            "@9": (
                "@9",
                "type_decl",
                [("name", "@13"), ("type", "@1"), ("srcp", "<built-in>:0"), ("note", "artificial")],
            ),
            "@13": ("@13", "identifier_node", [("strg", "void"), ("lngt", "4")]),
        }
        content = LangContent(data_dict)
        entry_tree = get_entry_tree(content)
        nodes_list = EntryTreeDepthFirstTraversal.to_list(entry_tree)

        self.assertEqual(9, len(nodes_list))
