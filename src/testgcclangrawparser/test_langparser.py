#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest

from gcclangrawparser.langparser import ProprertiesConverter


class ProprertiesConverterTest(unittest.TestCase):

    def test_convert_colon(self):
        # colon in value field
        converter = ProprertiesConverter()
        props_dict = converter.convert("srcp: <built-in>:0 note: artificial")
        self.assertDictEqual({"note": "artificial", "srcp": "<built-in>:0"}, props_dict)

    def test_convert_double_colon(self):
        # double colo as value of namespace
        converter = ProprertiesConverter()
        props_dict = converter.convert("strg: ::       lngt: 2")
        self.assertDictEqual({"lngt": "2", "strg": "::"}, props_dict)

    def test_convert_space(self):
        # space in value field
        converter = ProprertiesConverter()
        props_dict = converter.convert("strg: long int lngt: 8")
        self.assertDictEqual({"lngt": "8", "strg": "long int"}, props_dict)

    def test_convert_ptd(self):
        # it seems that 'ptd' property has invalid space (gcc bug?)
        converter = ProprertiesConverter()
        props_dict = converter.convert("algn: 64       ptd : @653")
        self.assertDictEqual({"algn": "64", "ptd": "@653"}, props_dict)

    def test_convert_statement_list(self):
        # it seems that 'ptd' property has invalid space (gcc bug?)
        converter = ProprertiesConverter()
        props_dict = converter.convert("0   : @46      1   : @47")
        self.assertDictEqual({"0": "@46", "1": "@47"}, props_dict)

    def test_convert_op(self):
        converter = ProprertiesConverter()
        props_dict = converter.convert("type: @23      op 0: @49      op 1: @50     ")
        self.assertDictEqual({"type": "@23", "op 0": "@49", "op 1": "@50"}, props_dict)
