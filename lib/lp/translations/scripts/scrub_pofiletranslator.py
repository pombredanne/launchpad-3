# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Keep `POFileTranslator` more or less consistent with the real data."""

__metaclass__ = type
__all__ = [
    'ScrubPOFileTranslator',
    ]

from storm.expr import (
    Coalesce,
    Desc,
    )
import transaction

from lp.services.database.lpstorm import IStore
from lp.services.scripts.base import LaunchpadCronScript
from lp.translations.model.pofile import POFile
from lp.translations.model.pofiletranslator import POFileTranslator
from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationmessage import TranslationMessage
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )


class ScrubPOFileTranslator(LaunchpadCronScript):
    """Update `POFileTranslator` to reflect current translations."""

    def get_pofiles(self):
        """Retrieve POFiles to scrub.

        The result's ordering is aimed at maximizing cache effectiveness:
        by POTemplate name for locality of shared POTMsgSets, and by language
        for locality of shared TranslationMessages.
        """
        store = IStore(POFile)
        query = store.find(
            POFile,
            POFile.potemplateID == POTemplate.id,
            POTemplate.iscurrent == True)
        return query.order_by(POTemplate.name, POFile.languageID)

    def get_contributions(self, pofile):
        """Map all users' most recent contributions to `pofile`.

        Returns a dict mapping `Person` id to the creation time of their most
        recent `TranslationMessage` in `POFile`.
        """
        store = IStore(pofile)
        potmsgset_ids = store.find(
            TranslationTemplateItem.potmsgsetID,
            TranslationTemplateItem.potemplateID == pofile.potemplate.id,
            TranslationTemplateItem.sequence > 0)
        contribs = store.find(
            (TranslationMessage.submitterID, TranslationMessage.date_created),
            TranslationMessage.potmsgsetID.is_in(potmsgset_ids),
            TranslationMessage.languageID == pofile.language.id,
            TranslationMessage.msgstr0 != None,
            Coalesce(
                TranslationMessage.potemplateID,
                pofile.potemplate.id) == pofile.potemplate.id)
        contribs = contribs.config(distinct=(TranslationMessage.submitterID,))
        contribs = contribs.order_by(
            TranslationMessage.submitterID,
            Desc(TranslationMessage.date_created))
        return dict(contribs)

    def get_pofiletranslators(self, pofile):
        """Get `POFileTranslator` entries for `pofile`.

        Returns a dict mapping each contributor's person id to their
        `POFileTranslator` record.
        """
        store = IStore(pofile)
        pofts = store.find(
            POFileTranslator, POFileTranslator.pofileID == pofile.id)
        return {poft.personID: poft for poft in pofts}

    def remove_pofiletranslators(self, pofile, person_ids):
        """Delete `POFileTranslator` records."""
        self.logger.debug(
            "Removing %d POFileTranslator(s) for %s.",
            len(person_ids), pofile.title)
        store = IStore(pofile)
        pofts = store.find(
            POFileTranslator,
            POFileTranslator.pofileID == pofile.id,
            POFileTranslator.personID.is_in(person_ids))
        pofts.remove()

    def remove_unwarranted_pofiletranslators(self, pofile, pofts, contribs):
        """Delete `POFileTranslator` records that shouldn't be there."""
        excess = set(pofts) - set(contribs)
        if len(excess) > 0:
            self.remove_pofiletranslators(pofile, excess)

    def create_missing_pofiletranslators(self, pofile, pofts, contribs):
        """Create `POFileTranslator` records that were missing."""
        shortage = set(contribs) - set(pofts)
        if len(shortage) == 0:
            return
        self.logger.debug(
            "Adding %d POFileTranslator(s) for %s.",
            len(shortage), pofile.title)
        store = IStore(pofile)
        for missing_contributor in shortage:
            store.add(POFileTranslator(
                pofile=pofile, personID=missing_contributor,
                date_last_touched=contribs[missing_contributor]))

    def scrub_pofile(self, pofile):
        """Scrub `POFileTranslator` entries for one `POFile`.

        Removes inappropriate entries and adds missing ones.
        """
        contribs = self.get_contributions(pofile)
        pofiletranslators = self.get_pofiletranslators(pofile)
        self.remove_unwarranted_pofiletranslators(
            pofile, pofiletranslators, contribs)
        self.create_missing_pofiletranslators(
            pofile, pofiletranslators, contribs)

    def main(self):
        """See `LaunchpadScript`."""
        for pofile in self.get_pofiles():
            self.scrub_pofile(pofile)
            transaction.commit()
