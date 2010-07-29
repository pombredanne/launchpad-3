# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Remove 'variant' usage in POFiles and TranslationMessages."""

__metaclass__ = type
__all__ = ['MigrateVariantsProcess']

import logging

from zope.component import getUtility
from zope.interface import implements

from storm.expr import In

from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import DBLoopTuner
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.services.worlddata.model.language import Language
from lp.translations.model.translationmessage import (
    TranslationMessage)


class ReplacerMixin:
    """Replaces `language` and `variant` on all contained objects."""

    def __init__(self, transaction, logger, title, contents, new_language):
        self.transaction = transaction
        self.logger = logger
        self.start_at = 0

        self.title = title
        self.language = new_language
        self.contents = list(contents)
        self.logger.info(
            "Figuring out %ss that need fixing: "
            "this may take a while..." % title)
        self.total = len(self.contents)
        self.logger.info(
            "Fixing up a total of %d %ss." % (self.total, self.title))
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    def isDone(self):
        """See `ITunableLoop`."""
        # When the main loop hits the end of the list of objects,
        # it sets start_at to None.
        return self.start_at is None

    def getNextBatch(self, chunk_size):
        """Return a batch of objects to work with."""
        end_at = self.start_at + int(chunk_size)
        self.logger.debug(
            "Getting %s[%d:%d]..." % (self.title, self.start_at, end_at))
        return self.contents[self.start_at: end_at]

    def __call__(self, chunk_size):
        """See `ITunableLoop`.

        Retrieve a batch of objects in ascending id order, and switch
        all of them to self.language and no variant.
        """
        object_ids = self.getNextBatch(chunk_size)
        # Avoid circular imports.
        from lp.translations.model.pofile import POFile

        if len(object_ids) == 0:
            self.start_at = None
        else:
            if self.title == 'TranslationMessage':
                results = self.store.find(TranslationMessage,
                                          In(TranslationMessage.id, object_ids))
                results.set(TranslationMessage.language==self.language,
                            variant=None)
            else:
                results = self.store.find(POFile,
                                          In(POFile.id, object_ids))
                results.set(POFile.language==self.language,
                            variant=None)

            self.transaction.commit()
            self.transaction.begin()

            self.start_at += len(object_ids)
            self.logger.info("Processed %d/%d of %s." % (
                self.start_at, self.total, self.title))


class TranslationMessageVariantReplacer(ReplacerMixin):
    """Replaces language on all `TranslationMessage`s with variants."""
    implements(ITunableLoop)

    def __init__(self, transaction, logger, tm_ids, new_language):
        super(TranslationMessageVariantReplacer, self).__init__(
            transaction, logger, 'TranslationMessage',
            tm_ids, new_language)


class POFileVariantReplacer(ReplacerMixin):
    """Replaces language on all `TranslationMessage`s with variants."""
    implements(ITunableLoop)

    def __init__(self, transaction, logger, pofile_ids, new_language):
        super(POFileVariantReplacer, self).__init__(
            transaction, logger, 'POFile', pofile_ids, new_language)


class MigrateVariantsProcess:
    """Mark all `POFile` translation credits as translated."""

    def __init__(self, transaction, logger=None):
        self.transaction = transaction
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger("migrate-variants")
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    def getPOFileIDsForLanguage(self, language, variant):
        # Avoid circular imports.
        from lp.translations.model.pofile import POFile
        return self.store.find(POFile.id,
                               POFile.languageID == language.id,
                               POFile.variant == variant)

    def getTranslationMessageIDsForLanguage(self, language, variant):
        return self.store.find(TranslationMessage.id,
                               TranslationMessage.languageID == language.id,
                               TranslationMessage.variant == variant)

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
        from lp.translations.model.pofile import POFile
        pofile_language_variants = self.store.find(
            (Language, POFile.variant),
            POFile.languageID==Language.id,
            POFile.variant!=None)
        translationmessage_language_variants = self.store.find(
            (Language, TranslationMessage.variant),
            TranslationMessage.languageID==Language.id,
            TranslationMessage.variant!=None)

        # XXX DaniloSegan 2010-07-26: ideally, we'd use an Union of
        # these two ResultSets, however, Storm doesn't treat two
        # columns of the same type on different tables as 'compatible'
        # (bug #610492).
        language_variants = set([])
        for language_variant in pofile_language_variants:
            language_variants.add(language_variant)
        for language_variant in translationmessage_language_variants:
            language_variants.add(language_variant)
        return language_variants

    def run(self):
        language_variants = self.fetchAllLanguagesWithVariants()
        if len(language_variants) == 0:
            self.logger.info("Nothing to do.")
        for language, variant in language_variants:
            self.logger.info(
                "Migrating %s (%s@%s)..." % (
                    language.englishname, language.code, variant))
            new_language = self.getOrCreateLanguage(language, variant)

            tm_ids = self.getTranslationMessageIDsForLanguage(
                language, variant)
            tm_loop = TranslationMessageVariantReplacer(
                self.transaction, self.logger,
                tm_ids, new_language)
            DBLoopTuner(tm_loop, 5, minimum_chunk_size=100).run()

            pofile_ids = self.getPOFileIDsForLanguage(
                language, variant)
            pofile_loop = POFileVariantReplacer(
                self.transaction, self.logger,
                pofile_ids, new_language)
            DBLoopTuner(pofile_loop, 5, minimum_chunk_size=10).run()

        self.logger.info("Done.")
