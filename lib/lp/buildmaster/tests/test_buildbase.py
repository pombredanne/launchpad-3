# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IBuildBase`."""

__metaclass__ = type

from datetime import datetime
import unittest

from canonical.config import config
from lp.buildmaster.interfaces.buildbase import IBuildBase
from lp.buildmaster.model.buildbase import BuildBase
from lp.testing import TestCase


class TestBuildBase(TestCase):
    """Tests for `IBuildBase`."""

    def disabled_test_build_base_provides_interface(self):
        # XXX: BuildBase is supposed to implement IBuildBase, but doesn't atm.
        # Since it's not the focus of the branch, we'll postpone the work.
        build_base = BuildBase()
        self.assertProvides(build_base, IBuildBase)

    def test_getUploaderCommand_begins_with_configuration(self):
        # getUploaderCommand returns the command to execute the uploader,
        # which is mostly set in the Launchpad configuration.
        config_args = list(config.builddmaster.uploader.split())
        build_base = BuildBase()
        uploader_command = build_base.getUploaderCommand()
        self.assertEqual(config_args, uploader_command[:len(config_args)])

    def test_getUploadLeaf(self):
        # getUploadLeaf returns the current time, followed by the build id.
        build_base = BuildBase()
        now = datetime.now()
        build_id = self.factory.getUniqueInteger()
        upload_leaf = build_base.getUploadLeaf(build_id, now=now)
        self.assertEqual(
            '%s-%s' % (now.strftime("%Y%m%d-%H%M%S"), build_id), upload_leaf)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
