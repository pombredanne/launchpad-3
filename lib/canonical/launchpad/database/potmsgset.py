# Zope interfaces
from zope.interface import implements
from zope.component import getUtility

# SQL imports
from sqlobject import ForeignKey, IntCol, StringCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
from canonical.launchpad.interfaces import IPOTMsgSet, ILanguageSet
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.pomsgset import POMsgSet
from canonical.launchpad.database.pomsgidsighting import POMsgIDSighting

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

    def flags(self):
        if self.flagscomment is None:
            return ()
        else:
            return [ flag for flag in
                self.flagscomment.replace(' ', '').split(',') if flag != '' ]

    def messageIDs(self):
        """See IPOTMsgSet."""
        results = POMsgID.select('''
            POMsgIDSighting.potmsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id AND
            POMsgIDSighting.inlastrevision = TRUE
            ''' % self.id, clauseTables=['POMsgIDSighting'],
            orderBy='POMsgIDSighting.pluralform')

        for pomsgid in results:
            yield pomsgid

    # XXX: Carlos Perello Marin 15/10/04: Review, not sure it's correct...
    def getMessageIDSighting(self, pluralForm, allowOld=False):
        """Return the message ID sighting that is current and has the
        plural form provided."""
        if allowOld:
            results = POMsgIDSighting.selectBy(
                potmsgsetID=self.id,
                pluralform=pluralForm)
        else:
            results = POMsgIDSighting.selectBy(
                potmsgsetID=self.id,
                pluralform=pluralForm,
                inlastrevision=True)

        if results.count() == 0:
            raise KeyError, pluralForm
        else:
            assert results.count() == 1

            return results[0]

    def poMsgSet(self, language_code, variant=None):
        if variant is None:
            variantspec = 'IS NULL'
        elif isinstance(variant, unicode):
            variantspec = (u'= "%s"' % quote(variant))
        else:
            raise TypeError('Variant must be None or unicode.')

        sets = POMsgSet.select('''
            POMsgSet.potmsgset = %d AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            ''' % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=('POFile', 'Language'))

        if sets.count() == 0:
            raise KeyError, (language_code, variant)
        else:
            return sets[0]

    def translationsForLanguage(self, language):
        # Find the number of plural forms.

        # XXX: Not sure if falling back to the languages table is the right
        # thing to do.
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
                "Don't know the number of plural forms for this PO file!")

        if pofile is None:
            return [None] * pluralforms

        # Find the sibling message set.

        results = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d'''
           % (pofile.id, self.primemsgid_.id),
           clauseTables = ['POTMsgSet', ])

        if not (0 <= results.count() <= 1):
            raise AssertionError("Duplicate message ID in PO file.")

        if results.count() == 0:
            return [None] * pluralforms

        translation_set = results[0]

        results = list(POTranslationSighting.select(
            'pomsgset = %d AND active = TRUE' % translation_set.id,
            orderBy='pluralForm'))

        translations = []

        for form in range(pluralforms):
            if results and results[0].pluralform == form:
                translations.append(results.pop(0).potranslation.translation)
            else:
                translations.append(None)

        return translations

    # Methods defined in IEditPOTMsgSet

    def makeMessageIDSighting(self, text, pluralForm, update=False):
        """Create a new message ID sighting for this message set."""

        # This method used to accept 'text' parameters being string objects,
        # but this is depracated.
        if not isinstance(text, unicode):
            raise TypeError("Message ID text must be unicode.")

        try:
            messageID = POMsgID.byMsgid(text)
        except SQLObjectNotFound:
            messageID = POMsgID(msgid=text)

        existing = POMsgIDSighting.selectBy(
            potmsgsetID=self.id,
            pomsgid_ID=messageID.id,
            pluralform=pluralForm)

        if existing.count():
            assert existing.count() == 1

            if not update:
                raise KeyError(
                    "There is already a message ID sighting for this "
                    "message set, text, and plural form")

            existing = existing[0]
            existing.set(datelastseen = UTC_NOW, inlastrevision = True)

            return existing

        return POMsgIDSighting(
            potmsgsetID=self.id,
            pomsgid_ID=messageID.id,
            datefirstseen=UTC_NOW,
            datelastseen=UTC_NOW,
            inlastrevision=True,
            pluralform=pluralForm)
