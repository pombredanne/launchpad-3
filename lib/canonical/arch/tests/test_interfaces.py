#!/usr/bin/env python

# arch-tag: d7be3bf8-9f05-401c-9ffc-06f4dd19af48
# Author: David Allouche <david.allouche@canonical.com>
# Copyright (C) 2004 Canonical Software

"""Test suite for Canonical arch modules."""

import unittest
import sys

class TestImports(unittest.TestCase):
    def testBroker(self):
        from canonical.arch import broker


import framework
framework.register(__name__)
