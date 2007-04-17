# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POTMsgSet']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey, IntCol, StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote, sqlvalues

from canonical.launchpad.interfaces import (
    IPOTMsgSet, ILanguageSet, NotFoundError, NameNotAvailable, BrokenTextError
    )
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.pomsgset import POMsgSet, DummyPOMsgSet
from canonical.launchpad.database.pomsgidsighting import POMsgIDSighting
from canonical.launchpad.database.posubmission import POSubmission


class POTMsgSet(SQLBase):
    implements(IPOTMsgSet)

    _table = 'POTMsgSet'

    primemsgid_ = ForeignKey(foreignKey='POMsgID', dbName='primemsgid',
        notNull=True)
    sequence = IntCol(dbName='sequence', notNull=True)
    potemplate = ForeignKey(foreignKey='POTemplate', dbName='potemplate',
        notNull=True)
    commenttext = StringCol(dbName='commenttext', notNull=False)
    filereferences = StringCol(dbName='filereferences', notNull=False)
    sourcecomment = StringCol(dbName='sourcecomment', notNull=False)
    flagscomment = StringCol(dbName='flagscomment', notNull=False)

    def getCurrentSubmissions(self, language, pluralform):
        """See IPOTMsgSet."""
        return POSubmission.select('''
            POSubmission.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = %s AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %s AND
            POSubmission.pluralform = %s AND
            (POSubmission.active OR POSubmission.published)
            ''' % sqlvalues(language, self.primemsgid_, pluralform),
            clauseTables=['POTMsgSet', 'POMsgSet', 'POFile'],
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

    def getPOMsgIDs(self):
        """See IPOTMsgSet."""
        return POMsgID.select('''
            POMsgIDSighting.potmsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id AND
            POMsgIDSighting.inlastrevision = TRUE
            ''' % self.id,
            clauseTables=['POMsgIDSighting'],
            orderBy='POMsgIDSighting.pluralform')

    def getPOMsgIDSighting(self, pluralForm):
        """See IPOTMsgSet."""
        sighting = POMsgIDSighting.selectOneBy(
            potmsgset=self,
            pluralform=pluralForm,
            inlastrevision=True)
        if sighting is None:
            raise NotFoundError(pluralForm)
        else:
            return sighting

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
                self.primemsgid_.msgid, pofile.title))

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
        if len(list(self.getPOMsgIDs())) == 1:
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

        existing = POMsgIDSighting.selectOneBy(
            potmsgset=self,
            pomsgid_=messageID,
            pluralform=pluralForm)

        if existing is None:
            return POMsgIDSighting(
                potmsgset=self,
                pomsgid_=messageID,
                datefirstseen=UTC_NOW,
                datelastseen=UTC_NOW,
                inlastrevision=True,
                pluralform=pluralForm)
        else:
            if not update:
                raise NameNotAvailable(
                    "There is already a message ID sighting for this "
                    "message set, text, and plural form")
            existing.set(datelastseen=UTC_NOW, inlastrevision=True)
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
        if u'\u2022' in self.primemsgid_.msgid or u'\u2022' not in text:
            return text

        return text.replace(u'\u2022', ' ')

    def normalizeWhitespaces(self, text):
        """See IPOTMsgSet."""
        if text is None:
            return text

        msgid = self.primemsgid_.msgid
        stripped_msgid = msgid.strip()
        stripped_text = text.strip()
        new_text = None

        if len(stripped_msgid) > 0 and len(stripped_text) == 0:
            return ''

        if len(stripped_msgid) != len(msgid):
            # There are whitespaces that we should copy to the 'text'
            # after stripping it.
            prefix = msgid[:-len(msgid.lstrip())]
            postfix = msgid[len(msgid.rstrip()):]
            new_text = '%s%s%s' % (prefix, stripped_text, postfix)
        elif len(stripped_text) != len(text):
            # msgid does not have any whitespace, we need to remove
            # the extra ones added to this text.
            new_text = stripped_text
        else:
            # The text is not changed.
            new_text = text

        return new_text

    def normalizeNewLines(self, text):
        """See IPOTMsgSet."""
        msgid = self.primemsgid_.msgid
        # There are three different kinds of newlines:
        windows_style = '\r\n'
        mac_style = '\r'
        unix_style = '\n'
        # We need the stripped variables because a 'windows' style will be at
        # the same time a 'mac' and 'unix' style.
        stripped_text = text.replace(windows_style, '')
        stripped_msgid = msgid.replace(windows_style, '')

        # Get the style that uses the msgid.
        msgid_style = None
        if windows_style in msgid:
            msgid_style = windows_style

        if mac_style in stripped_msgid:
            if msgid_style is not None:
                raise BrokenTextError(
                    "msgid (%r) mixes different newline markers" % msgid)
            msgid_style = mac_style

        if unix_style in stripped_msgid:
            if msgid_style is not None:
                raise BrokenTextError(
                    "msgid (%r) mixes different newline markers" % msgid)
            msgid_style = unix_style

        # Get the style that uses the given text.
        text_style = None
        if windows_style in text:
            text_style = windows_style

        if mac_style in stripped_text:
            if text_style is not None:
                raise BrokenTextError(
                    "text (%r) mixes different newline markers" % text)
            text_style = mac_style

        if unix_style in stripped_text:
            if text_style is not None:
                raise BrokenTextError(
                    "text (%r) mixes different newline markers" % text)
            text_style = unix_style

        if msgid_style is None or text_style is None:
            # We don't need to do anything, the text is not changed.
            return text

        # Fix the newline chars.
        return text.replace(text_style, msgid_style)


    @property
    def hide_translations_from_anonymous(self):
        """See IPOTMsgSet."""
        return self.primemsgid_.msgid in [
            u'translation-credits',
            u'_: EMAIL OF TRANSLATORS\nYour emails'
            ]
