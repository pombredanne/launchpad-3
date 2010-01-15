# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IBuildBase`."""

__metaclass__ = type

from datetime import datetime
import os
import unittest

from canonical.config import config
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.buildmaster.interfaces.buildbase import IBuildBase
from lp.buildmaster.model.buildbase import BuildBase
from lp.registry.interfaces.pocket import pocketsuffix
from lp.testing import TestCase, TestCaseWithFactory


class TestBuildBase(TestCase):
    """Tests for `IBuildBase`."""

    def disabled_test_build_base_provides_interface(self):
        # XXX: BuildBase is supposed to implement IBuildBase, but doesn't atm.
        # Since it's not the focus of the branch, we'll postpone the work.
        build_base = BuildBase()
        self.assertProvides(build_base, IBuildBase)

    def test_getUploadLeaf(self):
        # getUploadLeaf returns the current time, followed by the build id.
        build_base = BuildBase()
        now = datetime.now()
        build_id = self.factory.getUniqueInteger()
        upload_leaf = build_base.getUploadLeaf(build_id, now=now)
        self.assertEqual(
            '%s-%s' % (now.strftime("%Y%m%d-%H%M%S"), build_id), upload_leaf)

    def test_getUploadDir(self):
        # getUploadDir is the absolute path to the directory in which things
        # are uploaded to.
        build_base = BuildBase()
        build_id = self.factory.getUniqueInteger()
        upload_leaf = build_base.getUploadLeaf(build_id)
        upload_dir = build_base.getUploadDir(upload_leaf)
        self.assertEqual(
            os.path.join(config.builddmaster.root, 'incoming', upload_leaf),
            upload_dir)


class TestBuildBaseHarder(TestCaseWithFactory):
    """Tests for `IBuildBase` that need objects from the rest of Launchpad."""

    layer = DatabaseFunctionalLayer

    def test_getUploaderCommand(self):
        build_base = BuildBase()
        upload_leaf = self.factory.getUniqueString('upload-leaf')
        build_base.distroseries = self.factory.makeDistroSeries()
        build_base.distribution = build_base.distroseries.distribution
        build_base.pocket = self.factory.getAnyPocket()
        build_base.id = self.factory.getUniqueInteger()
        build_base.policy_name = self.factory.getUniqueString('policy-name')
        config_args = list(config.builddmaster.uploader.split())
        log_file = os.path.join(
            build_base.getUploadDir(upload_leaf), 'uploader.log')
        config_args.extend(
            ['--log-file', log_file,
             '-d', build_base.distribution.name,
             '-s', (build_base.distroseries.name
                    + pocketsuffix[build_base.pocket]),
             '-b', str(build_base.id),
             '-J', upload_leaf,
             '--context=%s' % build_base.policy_name,
             os.path.abspath(config.builddmaster.root),
             ])
        uploader_command = build_base.getUploaderCommand(upload_leaf)
        self.assertEqual(config_args, uploader_command)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
