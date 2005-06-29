# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POTMsgSet']

import sets

from zope.interface import implements
from zope.component import getUtility
from zope.exceptions import NotFoundError

from sqlobject import ForeignKey, IntCol, StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote, sqlvalues

from canonical.launchpad.interfaces import IPOTMsgSet, ILanguageSet
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.pomsgset import POMsgSet
from canonical.launchpad.database.pomsgidsighting import POMsgIDSighting
from canonical.launchpad.database.poselection import POSelection
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

    def getWikiSubmissions(self, language, pluralform):
        """See IPOTMsgSet"""
        results = POSubmission.select("""
            POSubmission.pomsgset = POMsgSet.id AND
            POSubmission.pluralform = %d AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d""" % (pluralform,
                language.id, self.primemsgid_ID),
            clauseTables=['POMsgSet',
                          'POFile',
                          'POTMsgSet'],
            orderBy=['-datecreated'],
            distinct=True)
        submissions = sets.Set()
        translations = sets.Set()
        for submission in results:
            if submission.potranslation not in translations:
                translations.add(submission.potranslation)
                submissions.add(submission)
        result = sorted(list(submissions), key=lambda x: x.datecreated)
        result.reverse()
        return result


    def getCurrentSubmissions(self, language, pluralform):
        """See IPOTMsgSet"""
        selections = POSelection.select("""
            POSelection.pomsgset = POMsgSet.id AND
            POSelection.pluralform = %d AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d""" % (pluralform,
                language.id, self.primemsgid_ID),
            clauseTables=['POMsgSet',
                          'POFile',
                          'POTMsgSet'],
            distinct=True)
        submissions = sets.Set()
        translations = sets.Set()
        for selection in selections:
            if selection.activesubmission:
                if selection.activesubmission.potranslation not in translations:
                    submissions.add(selection.activesubmission)
                    translations.add(selection.activesubmission.potranslation)
            if selection.publishedsubmission:
                if selection.publishedsubmission.potranslation not in translations:
                    submissions.add(selection.publishedsubmission)
                    translations.add(selection.publishedsubmission.potranslation)
        result = sorted(list(submissions), key=lambda x: x.datecreated)
        result.reverse()
        return result

    def flags(self):
        if self.flagscomment is None:
            return []
        else:
            return [flag
                    for flag in self.flagscomment.replace(' ', '').split(',')
                    if flag != '']

    def messageIDs(self):
        """See IPOTMsgSet."""
        results = POMsgID.select('''
            POMsgIDSighting.potmsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id AND
            POMsgIDSighting.inlastrevision = TRUE
            ''' % self.id,
            clauseTables=['POMsgIDSighting'],
            orderBy='POMsgIDSighting.pluralform')

        for pomsgid in results:
            yield pomsgid

    # XXX: Carlos Perello Marin 15/10/04: Review, not sure it's correct...
    def getMessageIDSighting(self, pluralForm, allowOld=False):
        """Return the message ID sighting that is current and has the
        plural form provided.
        """
        if allowOld:
            sighting = POMsgIDSighting.selectOneBy(
                potmsgsetID=self.id,
                pluralform=pluralForm)
        else:
            sighting = POMsgIDSighting.selectOneBy(
                potmsgsetID=self.id,
                pluralform=pluralForm,
                inlastrevision=True)
        if sighting is None:
            raise KeyError, pluralForm
        else:
            return sighting

    def poMsgSet(self, language_code, variant=None):
        """See IPOTMsgSet."""
        if variant is None:
            variantspec = 'IS NULL'
        elif isinstance(variant, unicode):
            variantspec = (u'= "%s"' % quote(variant))
        else:
            raise TypeError('Variant must be None or unicode.')

        pomsgset = POMsgSet.selectOne('''
            POMsgSet.potmsgset = %d AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            ''' % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=['POFile', 'Language'])

        if pomsgset is None:
            raise NotFoundError(language_code, variant)
        return pomsgset

    def translationsForLanguage(self, language):
        # To start with, find the number of plural forms. We either want the
        # number set for this specific pofile, or we fall back to the
        # default for the language.

        languages = getUtility(ILanguageSet)
        try:
            pofile = self.potemplate.getPOFileByLang(language)
            pluralforms = pofile.pluralforms
        except KeyError:
            pofile = None
            pluralforms = languages[language].pluralforms

        # If we only have a msgid, we change pluralforms to 1, if it's a
        # plural form, it will be the number defined in the pofile header.
        if len(list(self.messageIDs())) == 1:
            pluralforms = 1

        if pluralforms == None:
            raise RuntimeError(
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

    # Methods defined in IEditPOTMsgSet

    def makeMessageIDSighting(self, text, pluralForm, update=False):
        """Create a new message ID sighting for this message set."""

        try:
            messageID = POMsgID.byMsgid(text)
        except SQLObjectNotFound:
            messageID = POMsgID(msgid=text)

        existing = POMsgIDSighting.selectOneBy(
            potmsgsetID=self.id,
            pomsgid_ID=messageID.id,
            pluralform=pluralForm)

        if existing is None:
            return POMsgIDSighting(
                potmsgsetID=self.id,
                pomsgid_ID=messageID.id,
                datefirstseen=UTC_NOW,
                datelastseen=UTC_NOW,
                inlastrevision=True,
                pluralform=pluralForm)
        else:
            if not update:
                raise KeyError(
                    "There is already a message ID sighting for this "
                    "message set, text, and plural form")
            existing.set(datelastseen=UTC_NOW, inlastrevision=True)
            return existing

