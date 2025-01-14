#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os


SCRIPT_DIR = os.path.dirname(__file__)


def get_data_root_path() -> str:
    return SCRIPT_DIR


def get_data_path(fileName: str) -> str:
    return os.path.join(get_data_root_path(), fileName)
