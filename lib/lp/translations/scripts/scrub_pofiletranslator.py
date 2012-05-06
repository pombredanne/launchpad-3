# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Keep `POFileTranslator` more or less consistent with the real data."""

__metaclass__ = type
__all__ = [
    'ScrubPOFileTranslator',
    ]


from lp.services.database.lpstorm import IStore
from lp.services.scripts.base import LaunchpadCronScript
from lp.translations.model.pofile import POFile
from lp.translations.model.potemplate import POTemplate


class ScrubPOFileTranslator(LaunchpadCronScript):
    """Update `POFileTranslator` to reflect current translations."""

    def get_pofiles(self):
        """Retrieve POFiles to scrub.

        The result's ordering is aimed at maximizing cache effectiveness:
        by POTemplate name for locality of shared POTMsgSets, and by language
        for locality of shared TranslationMessages.
        """
        store = IStore(POFile)
        query = store.find(POFile, POFile.potemplateID == POTemplate.id)
        return query.order_by(POTemplate.name, POFile.languageID)

    def scrub_pofile(self, pofile):
        """Scrub `POFileTranslator` entries for one `POFile`.

        Removes inappropriate entries and adds missing ones.
        """
        # TODO: Implement
        pass

    def main(self):
        """See `LaunchpadScript`."""
        for pofile in self.get_pofiles():
            self.scrub_pofile(pofile)
