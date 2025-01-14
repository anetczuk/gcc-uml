#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest

from gccuml.langparser import ProprertiesConverter, convert_lines_to_dict


class ProprertiesConverterTest(unittest.TestCase):

    def test_convert_colon(self):
        # colon in value field
        converter = ProprertiesConverter()
        props_dict = converter.convert("srcp: <built-in>:0 note: artificial")
        self.assertListEqual([("srcp", "<built-in>:0"), ("note", "artificial")], props_dict)

    def test_convert_double_colon(self):
        # double colo as value of namespace
        converter = ProprertiesConverter()
        props_dict = converter.convert("strg: ::       lngt: 2")
        self.assertListEqual([("strg", "::"), ("lngt", "2")], props_dict)

    def test_convert_space(self):
        # space in value field
        converter = ProprertiesConverter()
        props_dict = converter.convert("strg: long int lngt: 8")
        self.assertListEqual([("strg", "long int"), ("lngt", "8")], props_dict)

    def test_convert_ptd(self):
        # it seems that 'ptd' property has invalid space (gcc bug?)
        converter = ProprertiesConverter()
        props_dict = converter.convert("algn: 64       ptd : @653")
        self.assertListEqual([("algn", "64"), ("ptd", "@653")], props_dict)

    def test_convert_statement_list(self):
        # it seems that 'ptd' property has invalid space (gcc bug?)
        converter = ProprertiesConverter()
        props_dict = converter.convert("0   : @46      1   : @47")
        self.assertListEqual([("0", "@46"), ("1", "@47")], props_dict)

    def test_convert_op(self):
        converter = ProprertiesConverter()
        props_dict = converter.convert("type: @23      op 0: @49      op 1: @50     ")
        self.assertListEqual([("type", "@23"), ("op 0", "@49"), ("op 1", "@50")], props_dict)

    def test_convert_list(self):
        ## repeated props in data
        converter = ProprertiesConverter()
        props_dict = converter.convert(
            "       lngt: 2        idx : @50      val : @51                          idx : @52      val : @53"
        )
        self.assertListEqual(
            [("lngt", "2"), ("idx", "@50"), ("val", "@51"), ("idx", "@52"), ("val", "@53")], props_dict
        )


class LangParserTest(unittest.TestCase):

    def test_convert_lines_to_dict_repeated(self):
        data_list = list(
            [
                "@36     constructor      lngt: 2        idx : @50      val : @51"
                "                          idx : @52      val : @53"
            ]
        )
        ret_dict = convert_lines_to_dict(data_list)
        self.assertDictEqual(
            {
                "@36": (
                    "@36",
                    "constructor",
                    [("lngt", "2"), ("idx", "@50"), ("val", "@51"), ("idx", "@52"), ("val", "@53")],
                )
            },
            ret_dict,
        )
