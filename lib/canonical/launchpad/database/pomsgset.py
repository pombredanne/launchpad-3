
from canonical.database.sqlbase import SQLBase, quote

from types import NoneType
from datetime import datetime
from sets import Set

standardPOTemplateCopyright = 'Canonical Ltd'

import canonical.launchpad.interfaces as interfaces
from canonical.database.constants import nowUTC

from sqlobject import ForeignKey, MultipleJoin, RelatedJoin, IntCol, \
    BoolCol, StringCol, DateTimeCol, SQLObjectNotFound
from zope.interface import implements, directlyProvides
from zope.component import getUtility
from canonical.lp.dbschema import RosettaTranslationOrigin

from canonical.launchpad.database import Person

class POMessageSet(SQLBase):
    implements(interfaces.IEditPOTemplateOrPOFileMessageSet)

    _table = 'POMsgSet'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='POTemplate', dbName='potemplate', notNull=True),
        ForeignKey(name='poFile', foreignKey='POFile', dbName='pofile', notNull=False),
        ForeignKey(name='primeMessageID_', foreignKey='POMessageID', dbName='primemsgid', notNull=True),
        IntCol(name='sequence', dbName='sequence', notNull=True),
        BoolCol(name='isComplete', dbName='iscomplete', notNull=True),
        BoolCol(name='fuzzy', dbName='fuzzy', notNull=True),
        BoolCol(name='obsolete', dbName='obsolete', notNull=True),
        StringCol(name='commentText', dbName='commenttext', notNull=False),
        StringCol(name='fileReferences', dbName='filereferences', notNull=False),
        StringCol(name='sourceComment', dbName='sourcecomment', notNull=False),
        StringCol(name='flagsComment', dbName='flagscomment', notNull=False),
    ]

    def __init__(self, **kw):
        SQLBase.__init__(self, **kw)

        poFile = None

        if kw.has_key('poFile'):
            poFile = kw['poFile']

        if poFile is None:
            # this is a IPOTemplateMessageSet
            directlyProvides(self, interfaces.IPOTemplateMessageSet)
        else:
            # this is a IPOFileMessageSet
            directlyProvides(self, interfaces.IEditPOFileMessageSet)

    def flags(self):
        if self.flagsComment is None:
            return ()
        else:
            return [ flag for flag in
                self.flagsComment.replace(' ', '').split(',') if flag != '' ]

    def messageIDs(self):
        return POMessageID.select('''
            POMsgIDSighting.pomsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id AND
            POMsgIDSighting.inlastrevision = TRUE
            ''' % self.id, clauseTables=('POMsgIDSighting',),
            orderBy='POMsgIDSighting.pluralform')

    def getMessageIDSighting(self, pluralForm, allowOld=False):
        """Return the message ID sighting that is current and has the
        plural form provided."""
        if allowOld:
            results = POMessageIDSighting.selectBy(
                poMessageSetID=self.id,
                pluralForm=pluralForm)
        else:
            results = POMessageIDSighting.selectBy(
                poMessageSetID=self.id,
                pluralForm=pluralForm,
                inLastRevision=True)

        if results.count() == 0:
            raise KeyError, pluralForm
        else:
            assert results.count() == 1

            return results[0]

    def pluralForms(self):
        if self.poFile is None:
            raise RuntimeError(
                "This method cannot be used with PO template message sets!")

        # we need to check a pot-set, if one exists, to find whether this set
        # *does* have plural forms, by looking at the number of message ids.
        # It's usually not safe to look at the message ids of this message set,
        # because if it's a po-set it may be incorrect; but if a pot-set can't
        # be found, then self is our best guess.
        try:
            potset = self.templateMessageSet()
        except KeyError:
            # set is obsolete... try to get the count from self, although
            # that's not 100% reliable
            # when/if we split tables, this shouldn't be necessary
            potset = self
        if potset.messageIDs().count() > 1:
            # has plurals
            return self.poFile.pluralForms
        else:
            # message set is singular
            return 1

    def templateMessageSet(self):
        if self.poFile is None:
            raise RuntimeError(
                "This method cannot be used with PO template message sets!")

        potset = POMessageSet.select('''
            poTemplate = %d AND
            poFile IS NULL AND
            primemsgid = %d
            ''' % (self.poTemplate.id, self.primeMessageID_.id))
        if potset.count() == 0:
            raise KeyError, self.primeMessageID_.msgid
        assert potset.count() == 1
        return potset[0]

    def translations(self):
        if self.poFile is None:
            raise RuntimeError(
                "This method cannot be used with PO template message sets!")

        pluralforms = self.pluralForms()
        if pluralforms is None:
            raise RuntimeError(
                "Don't know the number of plural forms for this PO file!")

        results = list(POTranslationSighting.select(
            'pomsgset = %d AND active = TRUE' % self.id,
            orderBy='pluralForm'))

        translations = []

        for form in range(pluralforms):
            if results and results[0].pluralForm == form:
                translations.append(results.pop(0).poTranslation.translation)
            else:
                translations.append(None)

        return translations

    def translationsForLanguage(self, language):
        if self.poFile is not None:
            raise RuntimeError(
                "This method cannot be used with PO file message sets!")

        # Find the number of plural forms.

        # XXX: Not sure if falling back to the languages table is the right
        # thing to do.
        languages = getUtility(interfaces.ILanguages)

        try:
            pofile = self.poTemplate.poFile(language)
            pluralforms = pofile.pluralForms
        except KeyError:
            pofile = None
            pluralforms = languages[language].pluralForms

        if self.messageIDs().count() == 1:
            pluralforms = 1

        if pluralforms == None:
            raise RuntimeError(
                "Don't know the number of plural forms for this PO file!")

        if pofile is None:
            return [None] * pluralforms

        # Find the sibling message set.

        results = POMessageSet.select('''pofile = %d AND primemsgid = %d'''
            % (pofile.id, self.primeMessageID_.id))

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
            if results and results[0].pluralForm == form:
                translations.append(results.pop(0).poTranslation.translation)
            else:
                translations.append(None)

        return translations

    def getTranslationSighting(self, pluralForm, allowOld=False):
        """Return the translation sighting that is committed and has the
        plural form specified."""
        if self.poFile is None:
            raise RuntimeError(
                "This method cannot be used with PO template message sets!")
        if allowOld:
            translations = POTranslationSighting.selectBy(
                poMessageSetID=self.id,
                pluralForm=pluralForm)
        else:
            translations = POTranslationSighting.selectBy(
                poMessageSetID=self.id,
                inLastRevision=True,
                pluralForm=pluralForm)
        if translations.count() == 0:
            raise IndexError, pluralForm
        else:
            return translations[0]

    def translationSightings(self):
        if self.poFile is None:
            raise RuntimeError(
                "This method cannot be used with PO template message sets!")
        return POTranslationSighting.selectBy(
            poMessageSetID=self.id)

    # IEditPOMessageSet

    def makeMessageIDSighting(self, text, pluralForm, update=False):
        """Create a new message ID sighting for this message set."""

        if type(text) is unicode:
            text = text.encode('utf-8')

        try:
            messageID = POMessageID.byMsgid(text)
        except SQLObjectNotFound:
            messageID = POMessageID(msgid=text)

        existing = POMessageIDSighting.selectBy(
            poMessageSetID=self.id,
            poMessageID_ID=messageID.id,
            pluralForm=pluralForm)

        if existing.count():
            assert existing.count() == 1

            if not update:
                raise KeyError(
                    "There is already a message ID sighting for this "
                    "message set, text, and plural form")

            existing = existing[0]
            existing.set(dateLastSeen = nowUTC, inLastRevision = True)

            return existing

        return POMessageIDSighting(
            poMessageSet=self,
            poMessageID_=messageID,
            dateFirstSeen=nowUTC,
            dateLastSeen=nowUTC,
            inLastRevision=True,
            pluralForm=pluralForm)

    def makeTranslationSighting(self, person, text, pluralForm,
                              update=False, fromPOFile=False):
        """Create a new translation sighting for this message set."""

        if self.poFile is None:
            raise RuntimeError(
                "This method cannot be used with PO template message sets!")

        # First get hold of a POTranslation for the specified text.
        try:
            translation = POTranslation.byTranslation(text)
        except SQLObjectNotFound:
            translation = POTranslation(translation=text)

        # Now get hold of any existing translation sightings.

        results = POTranslationSighting.selectBy(
            poMessageSetID=self.id,
            poTranslationID=translation.id,
            pluralForm=pluralForm,
            personID=person.id)

        if results.count():
            # A sighting already exists.

            assert results.count() == 1

            if not update:
                raise KeyError(
                    "There is already a translation sighting for this "
                    "message set, text, plural form and person.")

            sighting = results[0]
            sighting.set(
                dateLastActive = nowUTC,
                active = True,
                # XXX: Ugly!
                # XXX: Carlos Perello Marin 05/10/04 Why is ugly?
                inLastRevision = sighting.inLastRevision or fromPOFile)
        else:
            # No sighting exists yet.

            if fromPOFile:
                origin = int(RosettaTranslationOrigin.SCM)
            else:
                origin = int(RosettaTranslationOrigin.ROSETTAWEB)

            sighting = POTranslationSighting(
                poMessageSet=self,
                poTranslation=translation,
                dateFirstSeen= nowUTC,
                dateLastActive= nowUTC,
                inLastRevision=fromPOFile,
                pluralForm=pluralForm,
                active=True,
                person=person,
                origin=origin,
                # XXX: FIXME
                license=1)

        # Make all other sightings inactive.

        self._connection.query(
            '''
            UPDATE POTranslationSighting SET active = FALSE
            WHERE
                pomsgset = %d AND
                pluralform = %d AND
                id <> %d
            ''' % (self.id, pluralForm, sighting.id))

        return sighting


