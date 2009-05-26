# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from lp.testing import TestCase


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

