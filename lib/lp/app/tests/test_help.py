# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the help system integration."""

import os
import unittest

from zope.component import getUtility


from canonical.testing.layers import FunctionalLayer
from canonical.launchpad.layers import (
    AnswersLayer, BlueprintsLayer, BugsLayer, CodeLayer, LaunchpadLayer,
    TranslationsLayer)
from canonical.launchpad.testing.systemdocs import create_view
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

from canonical.lazr.folder import ExportedFolder

# The root of the tree
ROOT = os.path.realpath(
        os.path.join(
            os.path.dirname(__file__), os.path.pardir, os.path.pardir,
            os.path.pardir, os.path.pardir))


class TestHelpSystemSetup(unittest.TestCase):
    """Test that all help folders are registered on +help."""
    layer = FunctionalLayer

    def assertHasHelpFolderView(self, layer, expected_folder_path):
        """Assert that layer has +help help folder registered.
        It will make sure that the path is the expected one.
        """
        root = getUtility(ILaunchpadApplication)
        view = create_view(root, '+help', layer=layer)
        self.failUnless(
            isinstance(view, ExportedFolder),
            '+help view should be an instance of ExportedFolder: %s' % view)
        self.failUnless(
            os.path.samefile(view.folder, expected_folder_path),
            "Expected help folder %s, got %s" % (
                expected_folder_path, view.folder))

    def test_answers_help_folder(self):
        self.assertHasHelpFolderView(
            AnswersLayer, os.path.join(ROOT, 'lib/lp/answers/help'))

    def test_blueprints_help_folder(self):
        self.assertHasHelpFolderView(
            BlueprintsLayer,
            os.path.join(ROOT, 'lib/canonical/launchpad/help/blueprints'))

    def test_bugs_help_folder(self):
        self.assertHasHelpFolderView(
            BugsLayer,
            os.path.join(ROOT, 'lib/canonical/launchpad/help/bugs'))

    def test_code_help_folder(self):
        self.assertHasHelpFolderView(
            CodeLayer, os.path.join(ROOT, 'lib/lp/code/help'))

    def test_registry_help_folder(self):
        self.assertHasHelpFolderView(
            LaunchpadLayer,
            os.path.join(ROOT, 'lib/lp/registry/help'))

    def test_translations_help_folder(self):
        self.assertHasHelpFolderView(
            TranslationsLayer,
            os.path.join(ROOT, 'lib/canonical/launchpad/help/translations'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
