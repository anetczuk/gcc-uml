#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest
from testgcclangrawparser.data import get_data_path

from gcclangrawparser.langcontent import LangContent
from gcclangrawparser.langparser import parse_raw
from gcclangrawparser.tool.inheritgraph import InheritanceData
from gcclangrawparser.diagram.classdiagram import ClassDiagramGenerator


class GetClassesInfoTest(unittest.TestCase):

    def test_args(self):
        inherit_raw_path = get_data_path("inherit_args.cpp.003l.raw")
        content: LangContent = parse_raw(inherit_raw_path)
        content.convert_entries()

        inherit_data = InheritanceData(content)
        classes_info = inherit_data.generate_data()

        classes_list = list(classes_info.values())
        self.assertEqual(1, len(classes_list))

        info: ClassDiagramGenerator.ClassData = classes_list[0]
        self.assertEqual("::items::Abc1", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(3, len(method_list))

        method = method_list[0]
        self.assertEqual("call1_param", method.name)
        self.assertEqual("void", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)

        arg_list = method.args
        self.assertEqual(3, len(arg_list))
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramA", "int"), arg_list[0])
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramB", "double const"), arg_list[1])
        self.assertEqual(ClassDiagramGenerator.FunctionArg(None, "bool"), arg_list[2])

        method = method_list[1]
        self.assertEqual("call2_ptr", method.name)
        self.assertEqual("void", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)

        arg_list = method.args
        self.assertEqual(4, len(arg_list))
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramA", "int *"), arg_list[0])
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramB", "int const *"), arg_list[1])
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramC", "int const *"), arg_list[2])
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramD", "int * const"), arg_list[3])

        method = method_list[2]
        self.assertEqual("call3_ref", method.name)
        self.assertEqual("void", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)

        arg_list = method.args
        self.assertEqual(3, len(arg_list))
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramA", "int &"), arg_list[0])
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramB", "int const &"), arg_list[1])
        self.assertEqual(ClassDiagramGenerator.FunctionArg("paramC", "int const &"), arg_list[2])

    def test_methods(self):
        inherit_raw_path = get_data_path("inherit_meths.cpp.003l.raw")
        content: LangContent = parse_raw(inherit_raw_path)
        content.convert_entries()

        inherit_data = InheritanceData(content)
        classes_info = inherit_data.generate_data()

        classes_list = list(classes_info.values())
        self.assertEqual(3, len(classes_list))

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[0]
        self.assertEqual("::items::Abc3", info.name)
        self.assertEqual([ClassDiagramGenerator.ClassBase(name="::items::Abc2", access="pub")], info.bases)
        self.assertEqual([ClassDiagramGenerator.ClassField(name="field", type="int", access="public")], info.fields)

        method_list = info.methods
        self.assertEqual(7, len(method_list))

        method = method_list[0]
        self.assertEqual("callfunc3", method.name)
        self.assertEqual("void", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        method = method_list[1]
        self.assertEqual("callfunc4", method.name)
        self.assertEqual("int", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        method = method_list[2]
        self.assertEqual("callfunc5", method.name)
        self.assertEqual("bool", method.type)
        self.assertEqual("const", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        method = method_list[3]
        self.assertEqual("callfunc6_ptr1", method.name)
        self.assertEqual("int *", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        method = method_list[4]
        self.assertEqual("callfunc6_ptr2", method.name)
        self.assertEqual("int const *", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        method = method_list[5]
        self.assertEqual("callfunc6_ref", method.name)
        self.assertEqual("int &", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        method = method_list[6]
        self.assertEqual("callfunc6_ref2", method.name)
        self.assertEqual("int const &", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[1]
        self.assertEqual("::items::Abc2", info.name)
        self.assertEqual([ClassDiagramGenerator.ClassBase(name="::items::Abc1", access="pub")], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(1, len(method_list))

        method = method_list[0]
        self.assertEqual("callfunc2", method.name)
        self.assertEqual("void", method.type)
        self.assertEqual("virtual", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[2]
        self.assertEqual("::items::Abc1", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(3, len(method_list))

        method = method_list[0]
        self.assertEqual("Abc1", method.name)
        self.assertEqual("", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        method = method_list[1]
        self.assertEqual("callfunc1", method.name)
        self.assertEqual("void", method.type)
        self.assertEqual("virtual", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        method = method_list[2]
        self.assertEqual("callfunc2", method.name)
        self.assertEqual("void", method.type)
        self.assertEqual("virtual purevirt", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

    def test_ctors(self):
        inherit_raw_path = get_data_path("inherit_ctors.cpp.003l.raw")
        content: LangContent = parse_raw(inherit_raw_path)
        content.convert_entries()

        inherit_data = InheritanceData(content)
        classes_info = inherit_data.generate_data()

        classes_list = list(classes_info.values())
        self.assertEqual(8, len(classes_list))

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[0]
        self.assertEqual("::items::Abc3D", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(1, len(method_list))

        method = method_list[0]
        self.assertEqual("~Abc3D", method.name)
        self.assertEqual("", method.type)
        self.assertEqual("virtual", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[1]
        self.assertEqual("::items::Abc3C", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(1, len(method_list))

        method = method_list[0]
        self.assertEqual("~Abc3C", method.name)
        self.assertEqual("", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[2]
        self.assertEqual("::items::Abc3B", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(1, len(method_list))

        method = method_list[0]
        self.assertEqual("~Abc3B", method.name)
        self.assertEqual("", method.type)
        self.assertEqual("virtual default", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[3]
        self.assertEqual("::items::Abc3A", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(1, len(method_list))

        method = method_list[0]
        self.assertEqual("~Abc3A", method.name)
        self.assertEqual("", method.type)
        self.assertEqual("default", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[4]
        self.assertEqual("::items::Abc2", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(1, len(method_list))

        method = method_list[0]
        self.assertEqual("Abc2", method.name)
        self.assertEqual("", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([ClassDiagramGenerator.FunctionArg(name=None, type="::items::Abc2 const &")], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[5]
        self.assertEqual("::items::Abc1C", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(1, len(method_list))

        method = method_list[0]
        self.assertEqual("Abc1C", method.name)
        self.assertEqual("", method.type)
        self.assertEqual("", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[6]
        self.assertEqual("::items::Abc1B", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(1, len(method_list))

        method = method_list[0]
        self.assertEqual("Abc1B", method.name)
        self.assertEqual("", method.type)
        self.assertEqual("default", method.modifier)
        self.assertEqual("public", method.access)
        self.assertEqual([], method.args)

        # ==========================================

        info: ClassDiagramGenerator.ClassData = classes_list[7]
        self.assertEqual("::items::Abc1A", info.name)
        self.assertEqual([], info.bases)
        self.assertEqual([], info.fields)

        method_list = info.methods
        self.assertEqual(0, len(method_list))
