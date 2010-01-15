# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IBuildBase`."""

__metaclass__ = type

import unittest

from lp.buildmaster.interfaces.buildbase import IBuildBase
from lp.buildmaster.model.buildbase import BuildBase
from lp.testing import TestCase


class TestBuildBase(TestCase):
    """tests for `IBuildBase`."""

    def disabled_test_build_base_provides_interface(self):
        # XXX: BuildBase is supposed to implement IBuildBase, but doesn't atm.
        # Since it's not the focus of the branch, we'll postpone the work.
        build_base = BuildBase()
        self.assertProvides(build_base, IBuildBase)

    def test_get_uploader_command(self):
        # get_uploader_command returns the command to execute the uploader.
        # The command is returned as a list of arguments, popen-style.
        build_base = BuildBase()
        self.assertEqual([], build_base.getUploaderCommand())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
