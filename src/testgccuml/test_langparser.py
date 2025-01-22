#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest
from testgccuml.data import get_data_path

from gccuml.langparser import ProprertiesConverter, convert_lines_to_dict, parse_raw
from gccuml.langcontent import LangContent, Entry


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

    def test_consume_key_right_001(self):
        converter = ProprertiesConverter("aaa: ")
        value = converter.consume_key_right()
        self.assertEqual(b"aaa", value)

    def test_consume_key_right_002(self):
        converter = ProprertiesConverter("fld1: bbb  fld2:     ")
        value = converter.consume_key_right()
        self.assertEqual(b"fld2", value)

    def test_consume_key_right_003(self):
        converter = ProprertiesConverter("fld1: bbb  fld :     ")
        value = converter.consume_key_right()
        self.assertEqual(b"fld", value)

    def test_consume_word_right_001(self):
        converter = ProprertiesConverter("aaa     ")
        value = converter.consume_word_right()
        self.assertEqual(b"aaa", value)

    def test_consume_word_right_002(self):
        converter = ProprertiesConverter(" bbb aaa     ")
        value = converter.consume_word_right()
        self.assertEqual(b"aaa", value)

    def test_consume_type_field_decl_001(self):
        converter = ProprertiesConverter()
        props_dict = converter.convert_type_bytes(
            "field_decl",
            b"""name: @44      type: @45      scpe: @15
                         srcp: 20191015-2.c:5          chain: @46
                         accs: pub      bitfield       size: @47
                         algn: 1        bpos: @39     """,
        )
        self.assertListEqual(
            [
                ("name", "@44"),
                ("type", "@45"),
                ("scpe", "@15"),
                ("srcp", "20191015-2.c:5"),
                ("chain", "@46"),
                ("accs", "pub"),
                ("size", "@47"),
                ("algn", "1"),
                ("bpos", "@39"),
                ("bitfield", "1"),
            ],
            props_dict,
        )

    def test_consume_type_field_decl_002(self):
        converter = ProprertiesConverter()
        props_dict = converter.convert_type_bytes(
            "field_decl",
            b"""name: @344     type: @345     scpe: @176
                         srcp: inherit_sample.cpp:24
                         chain: @346     accs: pub      spec: mutable
                         bitfield      size: @347     algn: 1
                         bpos: @348    """,
        )
        self.assertListEqual(
            [
                ("name", "@344"),
                ("type", "@345"),
                ("scpe", "@176"),
                ("srcp", "inherit_sample.cpp:24"),
                ("chain", "@346"),
                ("accs", "pub"),
                ("spec", "mutable"),
                ("size", "@347"),
                ("algn", "1"),
                ("bpos", "@348"),
                ("bitfield", "1"),
            ],
            props_dict,
        )

    def test_consume_type_field_decl_003(self):
        converter = ProprertiesConverter()
        props_dict = converter.convert_type_bytes(
            "field_decl",
            b"""name: @344     type: @345     scpe: @176
                         srcp: inherit_sample.cpp:24
                         chain: @346     accs: pub      spec: mutable
                         bitfield: 1     size: @347     algn: 1
                         bpos: @348    """,
        )
        self.assertListEqual(
            [
                ("name", "@344"),
                ("type", "@345"),
                ("scpe", "@176"),
                ("srcp", "inherit_sample.cpp:24"),
                ("chain", "@346"),
                ("accs", "pub"),
                ("spec", "mutable"),
                ("bitfield", "1"),
                ("size", "@347"),
                ("algn", "1"),
                ("bpos", "@348"),
            ],
            props_dict,
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

    def test_convert_lines_to_dict_string_cst_inject_001(self):
        # test for injected field name in "strg"
        data_list = list(["@79     string_cst       type: @86     strg: lngt: 1  lngt: 8       "])
        ret_dict = convert_lines_to_dict(data_list)
        self.assertDictEqual(
            {"@79": ("@79", "string_cst", [("type", "@86"), ("strg", "lngt: 1"), ("lngt", "8")])},
            ret_dict,
        )

    def test_convert_lines_to_dict_string_cst_inject_002(self):
        # test for injected field name in "strg"
        data_list = list(["@73     string_cst       type: @78     strg: lngt: 1 lngt: 2  lngt: 16      "])
        ret_dict = convert_lines_to_dict(data_list)
        self.assertDictEqual(
            {"@73": ("@73", "string_cst", [("type", "@78"), ("strg", "lngt: 1 lngt: 2"), ("lngt", "16")])},
            ret_dict,
        )

    def test_convert_lines_to_dict_string_cst_inject_003(self):
        # test for injected field name in "strg"
        data_list = list(["@79     string_cst       type: @86     strg: lngt: 1  lngt: 8       "])
        ret_dict = convert_lines_to_dict(data_list)
        self.assertDictEqual(
            {"@79": ("@79", "string_cst", [("type", "@86"), ("strg", "lngt: 1"), ("lngt", "8")])},
            ret_dict,
        )

    def test_convert_lines_to_dict_string_cst_inject_004(self):
        # test for injected field name in "strg"
        data_list = list(
            ["""@48     string_cst       type: @46     strg: @?>=<;:9876543210/.-,+*)('&%$#" lngt: 32      """]
        )
        ret_dict = convert_lines_to_dict(data_list)
        self.assertDictEqual(
            {
                "@48": (
                    "@48",
                    "string_cst",
                    [("type", "@46"), ("strg", "@?>=<;:9876543210/.-,+*)('&%$#\""), ("lngt", "32")],
                )
            },
            ret_dict,
        )

    def test_parse_raw_string_cst_invalid_char(self):
        # invalid character
        invalid_char_raw_path: str = get_data_path("string_cst_invalidchar.003l.raw")
        content: LangContent = parse_raw(invalid_char_raw_path)
        string_cst_entry: Entry = content.get_entry_by_id("@65")
        self.assertTrue(string_cst_entry)
        length = string_cst_entry.get("lngt")
        self.assertEqual(length, "3")
        value = string_cst_entry.get("strg")
        self.assertEqual(value, "0xFF41FF")
