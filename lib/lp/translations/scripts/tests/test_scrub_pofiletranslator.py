# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test scrubbing of `POFileTranslator`."""

__metaclass__ = type

from lp.services.database.constants import UTC_NOW
from lp.services.database.lpstorm import IStore
from lp.services.scripts.tests import run_script
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessDatabaseLayer
from lp.translations.model.pofiletranslator import POFileTranslator
from lp.translations.scripts.scrub_pofiletranslator import (
    ScrubPOFileTranslator,
    )


def measure_distance(sequence, item1, item2):
    """Return the distance between items in a sequence."""
    container = list(sequence)
    return container.index(item2) - container.index(item1)


class TestScrubPOFileTranslator(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def make_script(self):
        return ScrubPOFileTranslator(test_args=[])

    def query_pofiletranslator(self, pofile, person):
        """Query `POFileTranslator` for a specific record.

        :return: Storm result set.
        """
        store = IStore(pofile)
        return store.find(POFileTranslator, pofile=pofile, person=person)

    def make_message_with_pofiletranslator(self, pofile=None):
        """Create a normal `TranslationMessage` with `POFileTranslator`."""
        if pofile is None:
            pofile = self.factory.makePOFile()
        potmsgset = self.factory.makePOTMsgSet(
            potemplate=pofile.potemplate, sequence=1)
        # A database trigger on TranslationMessage automatically creates
        # a POFileTranslator record for each new TranslationMessage.
        return self.factory.makeSuggestion(pofile=pofile, potmsgset=potmsgset)

    def make_message_without_pofiletranslator(self, pofile=None):
        """Create a `TranslationMessage` without `POFileTranslator`."""
        tm = self.make_message_with_pofiletranslator(pofile)
        self.becomeDbUser('postgres')
        self.query_pofiletranslator(pofile, tm.submitter).remove()
        return tm

    def make_pofiletranslator_without_message(self, pofile=None):
        """Create a `POFileTranslator` without `TranslationMessage`."""
        if pofile is None:
            pofile = self.factory.makePOFile()
        poft = POFileTranslator(
            pofile=pofile, person=self.factory.makePerson(),
            date_last_touched=UTC_NOW,
            # TODO: This argument can go once we've dropped latest_message.
            latest_message=self.factory.makeSuggestion())
        IStore(poft.pofile).add(poft)
        return poft

    def test_get_pofiles_gets_all_pofiles(self):
        pofile = self.factory.makePOFile()
        self.assertIn(pofile, self.make_script().get_pofiles())

    def test_get_pofiles_clusters_by_template_name(self):
        # POFiles for templates with the same name are bunched together
        # in the get_pofiles() output.
        templates = [
            self.factory.makePOTemplate(name='shared'),
            self.factory.makePOTemplate(name='other'),
            self.factory.makePOTemplate(name='andanother'),
            self.factory.makePOTemplate(
                name='shared', distroseries=self.factory.makeDistroSeries()),
            ]
        pofiles = [
            self.factory.makePOFile(potemplate=template)
            for template in templates]
        ordering = self.make_script().get_pofiles()
        self.assertEqual(
            1, abs(measure_distance(ordering, pofiles[0], pofiles[-1])))

    def test_get_pofiles_clusters_by_language(self):
        # POFiles for sharing templates and the same language are
        # bunched together in the get_pofiles() output.
        templates = [
            self.factory.makePOTemplate(
                name='shared', distroseries=self.factory.makeDistroSeries())
            for counter in range(2)]
        # POFiles per language & template.  We create these in a strange
        # way to avoid the risk of mistaking accidental orderings such
        # as per-id from being mistaken for the proper order.
        pofiles_per_language = {language: [] for language in ['nl', 'fr']}
        for language, pofiles in pofiles_per_language.items():
            for template in templates:
                pofiles.append(
                    self.factory.makePOFile(language, potemplate=template))

        ordering = self.make_script().get_pofiles()
        for pofiles in pofiles_per_language.values():
            self.assertEqual(
                1, abs(measure_distance(ordering, pofiles[0], pofiles[1])))

    def test_scrub_pofile_leaves_good_pofiletranslator_in_place(self):
        pofile = self.factory.makePOFile()
        tm = self.make_message_with_pofiletranslator(pofile)
        old_poft = self.query_pofiletranslator(pofile, tm.submitter).one()

        self.make_script().scrub_pofile(pofile)

        new_poft = self.query_pofiletranslator(pofile, tm.submitter).one()
        self.assertEqual(old_poft, new_poft)

    def test_scrub_pofile_deletes_unwarranted_entries(self):
        poft = self.make_pofiletranslator_without_message()

        self.make_script().scrub_pofile(poft.pofile)

        self.assertIsNone(
            self.query_pofiletranslator(poft.pofile, poft.person).one())

    def test_scrub_pofile_adds_missing_entries(self):
        pofile = self.factory.makePOFile()
        tm = self.make_message_without_pofiletranslator(pofile)

        self.make_script().scrub_pofile(pofile)

        new_poft = self.query_pofiletranslator(pofile, tm.submitter).one()
        self.assertEqual(tm.submitter, new_poft.person)
        self.assertEqual(pofile, new_poft.pofile)

    def test_script(self):
        pofile = self.factory.makePOFile()
        tm = self.make_message_without_pofiletranslator(pofile)
        bad_poft = self.make_pofiletranslator_without_message(pofile)

        retval, stdout, stderr = run_script(
            'cronscripts/scrub-pofiletranslator.py', [])

        self.assertIsNotNone(
            self.query_pofiletranslator(pofile, tm.submitter).one())
        self.assertIsNone(
            self.query_pofiletranslator(pofile, bad_poft.person).one())
