#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest

import logging
import io

from gccuml import logger


class LoggerTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        self.logger = logging.Logger(__name__)
        self.logger.propagate = False
        self.logger.setLevel(logging.DEBUG)
        self.buffer = io.StringIO()
        handler = logging.StreamHandler(self.buffer)
        formatter = logger.create_formatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def tearDown(self):
        ## Called after testfunction was executed
        self.logger = None
        self.buffer.close()
        self.buffer = None

    def test_empty_message(self):
        self.logger.info("")
        msg = self.buffer.getvalue()
        self.assertEqual(msg, "\n")

    def test_new_lines_linux(self):
        self.logger.info("\n\n\n")
        msg = self.buffer.getvalue()
        self.assertEqual(msg, "\n\n\n\n")

    def test_new_lines_windows(self):
        self.logger.info("\r\n\r\n\r\n")
        msg = self.buffer.getvalue()
        self.assertEqual(msg, "\r\n\r\n\r\n\n")
