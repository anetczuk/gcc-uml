#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import sys
import os


#### append source root - it is needed to directly run main.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


PKG_DIR = os.path.dirname(os.path.realpath(__file__))
TMP_DIR = os.path.abspath(os.path.join(PKG_DIR, os.pardir, os.pardir, "tmp"))
