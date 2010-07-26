# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


"""Remove 'variant' usage in POFiles and TranslationMessages."""

__metaclass__ = type
__all__ = ['MigrateVariantsProcess']

import logging

from zope.component import getUtility
from zope.interface import implements

from storm.expr import Coalesce, SQLRaw

from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import DBLoopTuner
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)
from lp.services.database.collection import Collection
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.services.worlddata.model.language import Language
from lp.translations.interfaces.pofile import IPOFileSet
from lp.translations.model.translationmessage import TranslationMessage


class TranslationMessagesCollection(Collection):
    """A `Collection` of `TranslationMessage`."""
    starting_table = TranslationMessage

    def __init__(self, *args, **kwargs):
        super(TranslationMessagesCollection, self).__init__(*args, **kwargs)

    def restrictLanguage(self, language, variant):
        """Restrict collection to a specific language."""
        new_collection = self.refine(
            TranslationMessage.languageID == language.id,
            TranslationMessage.variant == variant)
        return new_collection


class TranslationMessageVariantReplacer:
    """Replaces language on all `TranslationMessage`s with variants."""
    implements(ITunableLoop)

    def __init__(self, transaction, logger, language, variant, new_language):
        self.transaction = transaction
        self.logger = logger
        self.start_at = 0

        tm_collection = TranslationMessagesCollection(
            ).restrictLanguage(language, variant)
        self.language = new_language
        self.messages = tm_collection.select()
        self.logger.info(
            "Figuring out TranslationMessages that need fixing: "
            "this may take a while...")
        self.total = self.messages.count()
        self.logger.info(
            "Fixing up a total of %d translation messages." % self.total)

    def isDone(self):
        """See `ITunableLoop`."""
        # When the main loop hits the end of the list of TranslationMessages,
        # it sets start_at to None.
        return self.start_at is None

    def getNextBatch(self, chunk_size):
        """Return a batch of TranslationMessages to work with."""
        end_at = self.start_at + int(chunk_size)
        self.logger.debug(
            "Getting TranslationMessages[%d:%d]..." % (self.start_at, end_at))
        return self.messages[0: int(chunk_size)]

    def __call__(self, chunk_size):
        """See `ITunableLoop`.

        Retrieve a batch of `POFile`s in ascending id order, and mark
        all of their translation credits as translated.
        """
        messages = self.getNextBatch(chunk_size)

        done = 0
        for message in messages:
            done += 1
            self.logger.debug(
                "Processing %d (out of %d)" % (
                    self.start_at + done, self.total))
            message.language = self.language
            message.variant = None
            if done % 100 == 0:
                self.transaction.commit()
                self.logger.info("Committed. New transaction.")
                self.transaction.begin()

        self.transaction.commit()
        self.logger.info("Committed. All done.")
        self.transaction.begin()

        if done == 0:
            self.start_at = None
        else:
            self.start_at += done
            self.logger.info("Processed %d/%d of messages." % (
                self.start_at, self.total))


class MigrateVariantsProcess:
    """Mark all `POFile` translation credits as translated."""

    def __init__(self, transaction, logger=None):
        self.transaction = transaction
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger("migrate-variants")

    def getOrCreateLanguage(self, language, variant):
        """Create a language based on `language` and variant.

        Resulting language keeps the properties of parent language,
        but has a language code appended with the `variant`.
        """
        language_set = getUtility(ILanguageSet)
        new_code = '%s@%s' % (language.code, variant)
        new_language = language_set.getLanguageByCode(new_code)
        if new_language is None:
            new_language = language_set.createLanguage(
                new_code,
                englishname='%s %s' % (language.englishname, variant),
                pluralforms=language.pluralforms,
                pluralexpression=language.pluralexpression,
                visible=False,
                direction=language.direction)
            self.logger.info("Created language %s." % new_code)
        return new_language

    def fetchAllLanguagesWithVariants(self):
        store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        from lp.translations.model.pofile import POFile
        pofile_language_variants = store.find(
            (Language, POFile.variant),
            POFile.languageID==Language.id,
            POFile.variant!=None)
        translationmessage_language_variants = store.find(
            (Language, TranslationMessage.variant),
            TranslationMessage.languageID==Language.id,
            TranslationMessage.variant!=None)

        # XXX DaniloSegan 2010-07-26: ideally, we'd use an Union of
        # these two ResultSets, however, Storm doesn't treat two
        # columns of the same type on different tables as 'compatible'
        # (bug #...).
        language_variants = set([])
        for language_variant in pofile_language_variants:
            language_variants.add(language_variant)
        for language_variant in translationmessage_language_variants:
            language_variants.add(language_variant)
        return language_variants

    def run(self):
        for language, variant in self.fetchAllLanguagesWithVariants():
            self.logger.info(
                "Migrating %s (%s@%s)..." % (
                    language.englishname, language.code, variant))
            new_language = self.getOrCreateLanguage(language, variant)

            loop = TranslationMessageVariantReplacer(
                self.transaction, self.logger,
                language, variant, new_language)

            DBLoopTuner(loop, 5).run()

        self.logger.info("Done.")

