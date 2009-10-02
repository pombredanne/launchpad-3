# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Acceptance test for the translations-export-to-branch script."""

import re
import unittest
import transaction

from textwrap import dedent

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.scripts.tests import run_script
from canonical.testing import ZopelessAppServerLayer

from lp.testing import map_branch_contents, TestCaseWithFactory

from lp.translations.scripts.translations_to_branch import (
    ExportTranslationsToBranch)


class TestExportTranslationsToBranch(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def _filterOutput(self, output):
        """Remove DEBUG lines from output."""
        return '\n'.join([
            line for line in output.splitlines()
            if not line.startswith('DEBUG')])

    def test_translations_export_to_branch(self):
        # End-to-end test of the script doing its work.

        # Set up a server for hosted branches.
        self.useBzrBranches(real_server=True)

        # Set up a product and translatable series.
        product = self.factory.makeProduct(name='committobranch')
        product = removeSecurityProxy(product)
        series = product.getSeries('trunk')

        # Set up a translations_branch for the series.
        db_branch, tree = self.create_branch_and_tree(
            hosted=True, product=product)
        removeSecurityProxy(db_branch).last_scanned_id = 'null:'
        product.official_rosetta = True
        series.translations_branch = db_branch

        # Set up a template & Dutch translation for the series.
        template = self.factory.makePOTemplate(
            productseries=series, owner=product.owner, name='foo',
            path='po/messages.pot')
        template = removeSecurityProxy(template)
        potmsgset = self.factory.makePOTMsgSet(
            template, singular='Hello World', sequence=1)
        pofile = self.factory.makePOFile(
            'nl', potemplate=template, owner=product.owner)
        self.factory.makeTranslationMessage(
            pofile=pofile, potmsgset=potmsgset,
            translator=product.owner, reviewer=product.owner,
            translations=['Hallo Wereld'])

        # Make all this visible to the script we're about to run.
        transaction.commit()

        # Run The Script.
        retcode, stdout, stderr = run_script(
            'cronscripts/translations-export-to-branch.py', ['-vvv'])

        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Exporting to translations branches.\n'
            'INFO    Exporting Committobranch trunk series.\n'
            'INFO    Processed 1 item(s); 0 failure(s).',
            self._filterOutput(stderr))
        self.assertIn('No previous translations commit found.', stderr)
        self.assertEqual(0, retcode)

        # The branch now contains a snapshot of the translation.  (Only
        # one file: the Dutch translation we set up earlier).
        branch_contents = map_branch_contents(db_branch.getPullURL())
        expected_contents = {
            'po/nl.po': """
                # Dutch translation for .*
                # Copyright .*
                (?:#.*$
                )*msgid ""
                msgstr ""
                (?:"[^"]*"
                )*
                msgid "Hello World"
                msgstr "Hallo Wereld"\n""",
        }

        branch_filenames = set(branch_contents.iterkeys())
        expected_filenames = set(expected_contents.iterkeys())

        unexpected_filenames = branch_filenames - expected_filenames
        self.assertEqual(set(), unexpected_filenames)

        missing_filenames = expected_filenames - branch_filenames
        self.assertEqual(set(), missing_filenames)

        for filename, expected in expected_contents.iteritems():
            contents = branch_contents[filename].lstrip('\n')
            pattern = dedent(expected.lstrip('\n'))
            if not re.match(pattern, contents, re.MULTILINE):
                self.assertEqual(pattern, contents)

        # If we run the script again at this point, it won't export
        # anything because it sees that the POFile has not been changed
        # since the last export.
        retcode, stdout, stderr = run_script(
            'cronscripts/translations-export-to-branch.py',
            ['-vvv', '--no-fudge'])
        self.assertEqual(0, retcode)
        self.assertIn('Last commit was at', stderr)
        self.assertIn("Processed 1 item(s); 0 failure(s).", stderr)
        self.assertEqual(
            None, re.search("INFO\s+Committed [0-9]+ file", stderr))


class TestExportToStackedBranch(TestCaseWithFactory):
    """Test workaround for bzr bug 375013."""
    # XXX JeroenVermeulen 2009-10-02 bug=375013: Once bug 375013 is
    # fixed, this entire test can go.
    layer = ZopelessAppServerLayer

    def setUp(self):
        super(TestExportToStackedBranch, self).setUp()
        self.useBzrBranches()

        base_branch, tree = self.create_branch_and_tree(hosted=True)
        base_bzrbranch = tree.branch

        stacked_branch = self.factory.makeBranch(stacked_on=base_branch)
        stacked_bzrbranch = self.createBzrBranch(stacked_branch)
        stacked_bzrbranch.set_stacked_on_url(base_bzrbranch.base)

    def test_export_to_shared_branch(self):
        # The script knows how to deal with stacked branches.
        # Otherwise, this would fail.
        script = ExportTranslationsToBranch('reupload', test_args=[])
        committer = script._prepareBranchCommit(self.stacked_branch)
        try:
            self.assertNotEqual(None, committer)
            committer.writeFile('x.txt', 'x')
            committer.commit("x!")
        finally:
            committer.unlock()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
