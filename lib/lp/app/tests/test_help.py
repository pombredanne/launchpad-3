# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the help system integration."""

import os
import unittest

from zope.component import getUtility

from canonical.launchpad.layers import LaunchpadLayer
from canonical.launchpad.testing.systemdocs import create_view
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication
from canonical.lazr.folder import ExportedFolder
from canonical.testing.layers import FunctionalLayer
from lp.translations.publisher import TranslationsLayer

# The root of the tree
ROOT = os.path.realpath(
        os.path.join(
            os.path.dirname(__file__), os.path.pardir, os.path.pardir,
            os.path.pardir, os.path.pardir))


class TestHelpSystemSetup(unittest.TestCase):
    """Test that all help folders are registered."""
    layer = FunctionalLayer

    def assertHasHelpFolderView(self, name, expected_folder_path):
        """Assert that the named help folder has the right path."""
        view = create_view(getUtility(ILaunchpadApplication), name)
        self.failUnless(
            isinstance(view, ExportedFolder),
            'View should be an instance of ExportedFolder: %s' % view)
        self.failUnless(
            os.path.samefile(view.folder, expected_folder_path),
            "Expected help folder %s, got %s" % (
                expected_folder_path, view.folder))

    def test_answers_help_folder(self):
        self.assertHasHelpFolderView(
            '+help-answers', os.path.join(ROOT, 'lib/lp/answers/help'))

    def test_blueprints_help_folder(self):
        self.assertHasHelpFolderView(
            '+help-blueprints', os.path.join(ROOT, 'lib/lp/blueprints/help'))

    def test_bugs_help_folder(self):
        self.assertHasHelpFolderView(
            '+help-bugs', os.path.join(ROOT, 'lib/lp/bugs/help'))

    def test_code_help_folder(self):
        self.assertHasHelpFolderView(
            '+help-code', os.path.join(ROOT, 'lib/lp/code/help'))

    def test_registry_help_folder(self):
        self.assertHasHelpFolderView(
            '+help-registry', os.path.join(ROOT, 'lib/lp/registry/help'))

    def test_soyuz_help_folder(self):
        self.assertHasHelpFolderView(
            '+help-soyuz', os.path.join(ROOT, 'lib/lp/soyuz/help'))

    def test_translations_help_folder(self):
        self.assertHasHelpFolderView(
            '+help-translations',
            os.path.join(ROOT, 'lib/lp/translations/help'))
