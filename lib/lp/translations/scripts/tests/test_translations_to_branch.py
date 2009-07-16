# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Acceptance test for the translations-export-to-branch script."""

import re
import unittest
import transaction

from textwrap import dedent

from bzrlib.branch import Branch

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.scripts.tests import run_script
from canonical.testing import ZopelessAppServerLayer

from lp.testing import map_branch_contents, TestCaseWithFactory


class TestExportTranslationsToBranch(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_translations_export_to_branch(self):
        # End-to-end test of the script doing its work.
        self.useBzrBranches(real_server=True)
        product = self.factory.makeProduct(name='committobranch')
        product = removeSecurityProxy(product)
        series = product.getSeries('trunk')
        db_branch, tree = self.create_branch_and_tree(
            hosted=True, product=product)
        removeSecurityProxy(db_branch).last_scanned_id = 'null:'
        product.official_rosetta = True
        series.translations_branch = db_branch

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

        transaction.commit()

        retcode, stdout, stderr = run_script(
            'cronscripts/translations-export-to-branch.py', [])

        self.assertEqual('', stdout)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Exporting to translations branches.\n'
            'INFO    Exporting Committobranch trunk series.\n'
            'INFO    Processed 1 item(s); 0 failure(s).\n',
            stderr)
        self.assertEqual(0, retcode)

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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
