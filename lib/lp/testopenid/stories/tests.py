# Copyright 2004-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import unittest

import scandir

from lp.testing.pages import PageTestSuite


here = os.path.dirname(os.path.realpath(__file__))


def test_suite():
    stories = sorted(
        entry.name for entry in scandir.scandir(here)
        if not entry.name.startswith('.') and entry.is_dir())

    suite = unittest.TestSuite()
    suite.addTest(PageTestSuite('.'))
    for storydir in stories:
        suite.addTest(PageTestSuite(storydir))

    return suite
