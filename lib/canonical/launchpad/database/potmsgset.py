# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POTMsgSet']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey, IntCol, StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote, sqlvalues

from canonical.launchpad.interfaces import (
    BrokenTextError, ILanguageSet, IPOTMsgSet, ITranslationImporter,
    TranslationConstants)
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.pomsgset import POMsgSet, DummyPOMsgSet
from canonical.launchpad.database.pomsgidsighting import POMsgIDSighting
from canonical.launchpad.database.posubmission import POSubmission


class POTMsgSet(SQLBase):
    implements(IPOTMsgSet)

    _table = 'POTMsgSet'

    context = StringCol(dbName='context', notNull=False)
    primemsgid_ = ForeignKey(foreignKey='POMsgID', dbName='primemsgid',
        notNull=True)
    sequence = IntCol(dbName='sequence', notNull=True)
    potemplate = ForeignKey(foreignKey='POTemplate', dbName='potemplate',
        notNull=True)
    commenttext = StringCol(dbName='commenttext', notNull=False)
    filereferences = StringCol(dbName='filereferences', notNull=False)
    sourcecomment = StringCol(dbName='sourcecomment', notNull=False)
    flagscomment = StringCol(dbName='flagscomment', notNull=False)

    # XXX: JeroenVermeulen 2007-08-27: This field keeps track of a cached
    # value for msgid_plural.  We couldn't use @cachedproperty there because
    # @cachedproperty uses None for "not cached."  But for msgid_plural None
    # is a plausible cacheable value, so that wouldn't work.  The "phase 2"
    # Rosetta schema optimization will replace msgid_plural with a column, so
    # this custom caching machinery will disappear.  If that weren't the case,
    # we ought to extend @cachedproperty to support None as a value.
    has_cached_msgid_plural = False

    @property
    def msgid(self):
        """See IPOTMsgSet."""
        return self.primemsgid_.msgid

    @property
    def msgid_plural(self):
        """See IPOTMsgSet."""
        if self.has_cached_msgid_plural:
            return self.cached_msgid_plural

        self.cached_msgid_plural = None

        plural = POMsgID.selectOne('''
            POMsgIDSighting.potmsgset = %s AND
            POMsgIDSighting.pomsgid = POMsgID.id AND
            POMsgIDSighting.pluralform = 1 AND
            POMsgIDSighting.inlastrevision = TRUE
            ''' % sqlvalues(self),
            clauseTables=['POMsgIDSighting'])
        if plural is not None:
            self.cached_msgid_plural = plural.msgid

        self.has_cached_msgid_plural = True
        return self.cached_msgid_plural

    @property
    def singular_text(self):
        """See IPOTMsgSet."""
        format_importer = getUtility(
            ITranslationImporter).getTranslationFormatImporter(
                self.potemplate.source_file_format)
        if format_importer.uses_source_string_msgids:
            # This format uses English translations as the way to store the
            # singular_text.
            pomsgset = self.getPOMsgSet('en')
            if (pomsgset is not None and
                pomsgset.active_texts[
                    TranslationConstants.SINGULAR_FORM] is not None):
                return pomsgset.active_texts[
                    TranslationConstants.SINGULAR_FORM]

        # By default, singular text is the msgid.
        return self.msgid

    @property
    def plural_text(self):
        """See IPOTMsgSet."""
        return self.msgid_plural

    def getCurrentSubmissions(self, language, pluralform):
        """See IPOTMsgSet."""
        return POSubmission.select("""
            POSubmission.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = POFile.id AND
            POSubmission.id IN (
                SELECT POSubmission.id
                FROM
                    POSubmission
                    JOIN POMsgSet ON
                        POSubmission.pomsgset = POMsgSet.id
                    JOIN POFile ON
                        POMsgSet.pofile = POFile.id AND
                        POFile.language = %s
                    JOIN POTMsgSet ON
                        POMsgSet.potmsgset = POTMsgSet.id AND
                        POTMsgSet.primemsgid = %s
                    JOIN POTemplate ON
                        POTMsgSet.potemplate = POTemplate.id AND
                        POTemplate.iscurrent IS TRUE
                    LEFT JOIN ProductSeries ON
                        POTemplate.productseries = ProductSeries.id
                    LEFT JOIN Product ON
                        ProductSeries.product = Product.id
                    LEFT JOIN DistroSeries ON
                        POTemplate.distroseries = DistroSeries.id
                    LEFT JOIN Distribution ON
                        DistroSeries.distribution = Distribution.id
                WHERE
                    POSubmission.pluralform = %s AND
                    (POSubmission.active IS TRUE OR
                     POSubmission.published IS TRUE) AND
                    (Product.official_rosetta IS TRUE OR
                     Distribution.official_rosetta IS TRUE)
                )""" % sqlvalues(language, self.primemsgid_, pluralform),
            clauseTables=['POMsgSet', 'POFile'],
            orderBy='-datecreated',
            prejoinClauseTables=['POMsgSet', 'POFile'],
            prejoins=['potranslation', 'person'])

    def flags(self):
        if self.flagscomment is None:
            return []
        else:
            return [flag
                    for flag in self.flagscomment.replace(' ', '').split(',')
                    if flag != '']


    def getPOMsgSet(self, language_code, variant=None):
        """See IPOTMsgSet."""
        if variant is None:
            variantspec = 'IS NULL'
        else:
            variantspec = ('= %s' % quote(variant))

        return POMsgSet.selectOne('''
            POMsgSet.potmsgset = %d AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            ''' % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=['POFile', 'Language'])

    def getDummyPOMsgSet(self, language_code, variant=None):
        """See IPOTMsgSet."""
        # Make sure there's no existing POMsgSet for the given language and
        # variant
        if variant is None:
            variantspec = 'IS NULL'
        else:
            variantspec = ('= %s' % quote(variant))

        existing_pomsgset = POMsgSet.selectOne('''
            POMsgSet.potmsgset = %d AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            ''' % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=['POFile', 'Language'])

        pofile = self.potemplate.getPOFileByLang(language_code, variant)
        if pofile is None:
            pofile = self.potemplate.getDummyPOFile(language_code, variant)

        assert existing_pomsgset is None, (
            "There is already a valid IPOMsgSet for the '%s' msgid on %s" % (
                self.msgid, pofile.title))

        return DummyPOMsgSet(pofile, self)

    def translationsForLanguage(self, language):
        # To start with, find the number of plural forms. We either want the
        # number set for this specific pofile, or we fall back to the
        # default for the language.

        languages = getUtility(ILanguageSet)
        try:
            pofile = self.potemplate.getPOFileByLang(language)
        except KeyError:
            pofile = None
        pluralforms = languages[language].pluralforms

        # If we only have a msgid, we change pluralforms to 1, if it's a
        # plural form, it will be the number defined in the pofile header.
        if self.plural_text is None:
            pluralforms = 1

        assert pluralforms != None, (
                "Don't know the number of plural forms for this POT file!")

        # if we have no po file, then return empty translations
        if pofile is None:
            return [None] * pluralforms

        # Find the sibling message set.
        translation_set = POMsgSet.selectOne('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d'''
           % (pofile.id, self.primemsgid_.id),
           clauseTables = ['POTMsgSet'])

        if translation_set is None:
            return [None] * pluralforms

        return translation_set.active_texts

    def makeMessageIDSighting(self, text, pluralForm, update=False):
        """See IPOTMsgSet."""
        try:
            messageID = POMsgID.byMsgid(text)
        except SQLObjectNotFound:
            messageID = POMsgID(msgid=text)

        # Get current sighting so we can deactivate it, if needed.
        current_sighting = POMsgIDSighting.selectOneBy(
            potmsgset=self,
            pluralform=pluralForm,
            inlastrevision=True)

        existing = POMsgIDSighting.selectOneBy(
            potmsgset=self,
            pomsgid_=messageID,
            pluralform=pluralForm)

        if (current_sighting is not None and
            (existing is None or current_sighting != existing)):
            assert update, (
                "There is already a message ID sighting for this "
                "message set, text, and plural form")
            current_sighting.inlastrevision = False
            # We need to flush this change to prevent that the new one
            # that we are going to create conflicts with this due a race
            # condition applying the changes to the DB.
            current_sighting.syncUpdate()

        if pluralForm == TranslationConstants.SINGULAR_FORM:
            # Update direct link to the singular form.
            self.primemsgid_ = messageID
        elif pluralForm == TranslationConstants.PLURAL_FORM:
            # We may have had this cached, and it just changed.  Don't bother
            # updating cached value, just note we need to re-fetch it.
            self.has_cached_msgid_plural = False

        if existing is None:
            return POMsgIDSighting(
                potmsgset=self,
                pomsgid_=messageID,
                datefirstseen=UTC_NOW,
                datelastseen=UTC_NOW,
                inlastrevision=True,
                pluralform=pluralForm)
        else:
            existing.datelastseen = UTC_NOW
            existing.inlastrevision = True
            return existing

    def applySanityFixes(self, text):
        """See IPOTMsgSet."""

        # Fix the visual point that users copy & paste from the web interface.
        new_text = self.convertDotToSpace(text)
        # Now, fix the newline chars.
        new_text = self.normalizeNewLines(new_text)
        # And finally, set the same whitespaces at the start/end of the string.
        new_text = self.normalizeWhitespaces(new_text)

        return new_text

    def convertDotToSpace(self, text):
        """See IPOTMsgSet."""
        if u'\u2022' in self.singular_text or u'\u2022' not in text:
            return text

        return text.replace(u'\u2022', ' ')

    def normalizeWhitespaces(self, translation_text):
        """See IPOTMsgSet."""
        if translation_text is None:
            return None

        stripped_singular_text = self.singular_text.strip()
        stripped_translation_text = translation_text.strip()
        new_translation_text = None

        if (len(stripped_singular_text) > 0 and
            len(stripped_translation_text) == 0):
            return ''

        if len(stripped_singular_text) != len(self.singular_text):
            # There are whitespaces that we should copy to the 'text'
            # after stripping it.
            prefix = self.singular_text[:-len(self.singular_text.lstrip())]
            postfix = self.singular_text[len(self.singular_text.rstrip()):]
            new_translation_text = '%s%s%s' % (
                prefix, stripped_translation_text, postfix)
        elif len(stripped_translation_text) != len(translation_text):
            # msgid does not have any whitespace, we need to remove
            # the extra ones added to this text.
            new_translation_text = stripped_translation_text
        else:
            # The text is not changed.
            new_translation_text = translation_text

        return new_translation_text

    def normalizeNewLines(self, translation_text):
        """See IPOTMsgSet."""
        # There are three different kinds of newlines:
        windows_style = u'\r\n'
        mac_style = u'\r'
        unix_style = u'\n'
        # We need the stripped variables because a 'windows' style will be at
        # the same time a 'mac' and 'unix' style.
        stripped_translation_text = translation_text.replace(
            windows_style, u'')
        stripped_singular_text = self.singular_text.replace(windows_style, u'')

        # Get the style that uses singular_text.
        original_style = None
        if windows_style in self.singular_text:
            original_style = windows_style

        if mac_style in stripped_singular_text:
            if original_style is not None:
                raise BrokenTextError(
                    "original text (%r) mixes different newline markers" %
                        self.singular_text)
            original_style = mac_style

        if unix_style in stripped_singular_text:
            if original_style is not None:
                raise BrokenTextError(
                    "original text (%r) mixes different newline markers" %
                        self.singular_text)
            original_style = unix_style

        # Get the style that uses the given text.
        translation_style = None
        if windows_style in translation_text:
            translation_style = windows_style

        if mac_style in stripped_translation_text:
            if translation_style is not None:
                raise BrokenTextError(
                    "translation text (%r) mixes different newline markers" %
                        translation_text)
            translation_style = mac_style

        if unix_style in stripped_translation_text:
            if translation_style is not None:
                raise BrokenTextError(
                    "translation text (%r) mixes different newline markers" %
                        translation_text)
            translation_style = unix_style

        if original_style is None or translation_style is None:
            # We don't need to do anything, the text is not changed.
            return translation_text

        # Fix the newline chars.
        return translation_text.replace(translation_style, original_style)

    @property
    def hide_translations_from_anonymous(self):
        """See `IPOTMsgSet`."""
        # primemsgid_.msgid is pre-joined everywhere where
        # hide_translations_from_anonymous is used
        return self.primemsgid_.msgid in [
            u'translation-credits',
            u'translator-credits',
            u'translator_credits',
            u'_: EMAIL OF TRANSLATORS\nYour emails',
            u'Your emails',
            ]

    @property
    def is_translation_credit(self):
        """See `IPOTMsgSet`."""
        # primemsgid_.msgid is pre-joined everywhere where
        # is_translation_credit is used
        regular_credits = self.primemsgid_.msgid in [
            u'translation-credits',
            u'translator-credits',
            u'translator_credits' ]
        old_kde_credits = self.primemsgid_.msgid in [
            u'_: EMAIL OF TRANSLATORS\nYour emails',
            u'_: NAME OF TRANSLATORS\nYour names'
            ]
        kde_credits = ((self.primemsgid_.msgid == u'Your emails' and
                        self.context == u'EMAIL OF TRANSLATORS') or
                       (self.primemsgid_.msgid == u'Your names' and
                        self.context == u'NAME OF TRANSLATORS'))
        return (regular_credits or old_kde_credits or kde_credits)

    def makeHTMLId(self, suffix=None):
        """See `IPOTMsgSet`."""
        elements = ['msgset', str(self.id)]
        if suffix is not None:
            elements.append(suffix)
        return '_'.join(elements)
