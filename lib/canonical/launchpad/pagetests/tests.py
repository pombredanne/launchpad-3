# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run all of the pagetests, in priority order."""

__metaclass__ = type

import os
import unittest

from canonical.launchpad.testing.pages import PageTestSuite


here = os.path.dirname(os.path.realpath(__file__))


def test_suite():
    stories = sorted(
        dir for dir in os.listdir(here)
        if not dir.startswith('.') and os.path.isdir(os.path.join(here, dir)))

    suite = unittest.TestSuite()
    for storydir in stories:
        suite.addTest(PageTestSuite(storydir))

    return suite
