# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

import unittest

from lp.testing import TestCase


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
