#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest

from gccuml.langanalyze import get_entry_type_code_class
from gccuml.tool.ctrlflowgraph import (
    OP_UNARY_DICT,
    OP_BINARY_DICT,
    OP_COMPARISON_DICT,
    UNSUPPORTED_EXPRESSION_SET,
)


class CheckDictsTest(unittest.TestCase):

    def test_op_unary_dict(self):
        for item in OP_UNARY_DICT:
            item_type = get_entry_type_code_class(item)
            self.assertEqual("tcc_unary", item_type)

    def test_op_binary_dict(self):
        for item in OP_BINARY_DICT:
            item_type = get_entry_type_code_class(item)
            self.assertEqual("tcc_binary", item_type)

    def test_op_comparison_dict(self):
        for item in OP_COMPARISON_DICT:
            item_type = get_entry_type_code_class(item)
            self.assertEqual("tcc_comparison", item_type)

    def test_unsupported_expression_set(self):
        for item in UNSUPPORTED_EXPRESSION_SET:
            item_type = get_entry_type_code_class(item)
            self.assertEqual("tcc_expression", item_type, item)
