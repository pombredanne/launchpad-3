# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Runn test_logger.txt."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing.layers import BaseLayer
from lp.testing import TestCase
from canonical.launchpad.scripts.logger import LaunchpadFormatter
from sys import exc_info
from testtools.matchers import DocTestMatches
import doctest


DOCTEST_FLAGS = (
    doctest.ELLIPSIS |
    doctest.NORMALIZE_WHITESPACE |
    doctest.REPORT_NDIFF)


class TestLaunchpadFormatter(TestCase):
    """Tests of `LaunchpadFormatter`."""

    layer = BaseLayer

    def test_traceback_info(self):
        # LaunchpadFormatter inherits from zope.exceptions.log.Formatter, so
        # __traceback_info__ annotations are included in formatted exceptions.

        __traceback_info__ = "Captain Kirk"
        __traceback_info__

        try:
            0/0
        except ZeroDivisionError:
            info = exc_info()

        self.assertThat(
            LaunchpadFormatter().formatException(info),
            DocTestMatches(
                flags=DOCTEST_FLAGS, example="""
                    Traceback (most recent call last):
                    ...
                    __traceback_info__: Captain Kirk
                    ZeroDivisionError: integer division or modulo by zero
                    """))


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(
        LayeredDocFileSuite(
            'test_logger.txt', layer=BaseLayer))
    suite.addTest(
        loader.loadTestsFromName(__name__))
    return suite
