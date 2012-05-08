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
from lp.services.looptuner import TunableLoop
from lp.translations.model.pofile import POFile
from lp.translations.model.pofiletranslator import POFileTranslator
from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationmessage import TranslationMessage
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )


def get_pofiles():
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


def get_contributions(pofile):
    """Map all users' most recent contributions to `pofile`.

    Returns a dict mapping `Person` id to the creation time of their most
    recent `TranslationMessage` in `POFile`.

    This leaves some small room for error: a contribution that is masked by
    a diverged entry in this POFile will nevertheless produce a
    POFileTranslator record.  Fixing that would complicate the work more than
    it is probably worth.
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
        TranslationMessage.submitterID, Desc(TranslationMessage.date_created))
    return dict(contribs)


def get_pofiletranslators(pofile):
    """Get `POFileTranslator` entries for `pofile`.

    Returns a dict mapping each contributor's person id to their
    `POFileTranslator` record.
    """
    store = IStore(pofile)
    pofts = store.find(
        POFileTranslator, POFileTranslator.pofileID == pofile.id)
    return dict((poft.personID, poft) for poft in pofts)


def remove_pofiletranslators(logger, pofile, person_ids):
    """Delete `POFileTranslator` records."""
    logger.debug(
        "Removing %d POFileTranslator(s) for %s.",
        len(person_ids), pofile.title)
    store = IStore(pofile)
    pofts = store.find(
        POFileTranslator,
        POFileTranslator.pofileID == pofile.id,
        POFileTranslator.personID.is_in(person_ids))
    pofts.remove()


def remove_unwarranted_pofiletranslators(logger, pofile, pofts, contribs):
    """Delete `POFileTranslator` records that shouldn't be there."""
    excess = set(pofts) - set(contribs)
    if len(excess) > 0:
        remove_pofiletranslators(logger, pofile, excess)


def create_missing_pofiletranslators(logger, pofile, pofts, contribs):
    """Create `POFileTranslator` records that were missing."""
    shortage = set(contribs) - set(pofts)
    if len(shortage) == 0:
        return
    logger.debug(
        "Adding %d POFileTranslator(s) for %s.",
        len(shortage), pofile.title)
    store = IStore(pofile)
    for missing_contributor in shortage:
        store.add(POFileTranslator(
            pofile=pofile, personID=missing_contributor,
            date_last_touched=contribs[missing_contributor]))


def scrub_pofile(logger, pofile):
    """Scrub `POFileTranslator` entries for one `POFile`.

    Removes inappropriate entries and adds missing ones.
    """
    contribs = get_contributions(pofile)
    pofiletranslators = get_pofiletranslators(pofile)
    remove_unwarranted_pofiletranslators(
        logger, pofile, pofiletranslators, contribs)
    create_missing_pofiletranslators(
        logger, pofile, pofiletranslators, contribs)


class ScrubPOFileTranslator(TunableLoop):
    """Tunable loop, meant for running from inside Garbo."""

    maximum_chunk_size = 500

    def __init__(self, *args, **kwargs):
        super(ScrubPOFileTranslator, self).__init__(*args, **kwargs)
        # This does not listify the POFiles; they are batch-fetched on
        # demand.  So iteration may not be entirely exact, but it
        # doesn't really need to be.  It avoids loading all those
        # POFiles into memory when we only need a few per iteration.
        self.pofiles = get_pofiles()
        self.next_offset = 0

    def __call__(self, chunk_size):
        """See `ITunableLoop`."""
        start_offset = self.next_offset
        self.next_offset = start_offset + int(chunk_size)
        batch = list(self.pofiles[start_offset:self.next_offset])
        if len(batch) == 0:
            self.next_offset = None
        else:
            for pofile in batch:
                scrub_pofile(self.log, pofile)
            transaction.commit()

    def isDone(self):
        """See `ITunableLoop`."""
        return self.next_offset is None
