
from canonical.database.sqlbase import SQLBase, quote

from types import NoneType
from datetime import datetime
from sets import Set

standardPOTemplateCopyright = 'Canonical Ltd'

from canonical.lp.dbschema import RosettaTranslationOrigin
import canonical.launchpad.interfaces as interfaces
from canonical.database.constants import nowUTC
from canonical.launchpad.database.language import Language

from sqlobject import ForeignKey, MultipleJoin, RelatedJoin, IntCol, \
    BoolCol, StringCol, DateTimeCol, SQLObjectNotFound
from zope.interface import implements, directlyProvides
from zope.component import getUtility


# XXX: in the four strings below, we should fill in owner information
standardPOTemplateTopComment = ''' PO template for %(productname)s
 Copyright (c) %(copyright)s %(year)s
 This file is distributed under the same license as the %(productname)s package.
 PROJECT MAINTAINER OR MAILING LIST <EMAIL@ADDRESS>, %(year)s.

'''

# XXX: project-id-version needs a version
standardPOTemplateHeader = (
"Project-Id-Version: %(productname)s\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE NAME <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"X-Rosetta-Version: 0.1\n"
)

standardPOFileTopComment = ''' %(languagename)s translation for %(productname)s
 Copyright (c) %(copyright)s %(year)s
 This file is distributed under the same license as the %(productname)s package.
 FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.

'''

standardPOFileHeader = (
"Project-Id-Version: %(productname)s\n"
"Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>\n"
"POT-Creation-Date: %(templatedate)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: %(languagename)s <%(languagecode)s@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"X-Rosetta-Version: 0.1\n"
"Plural-Forms: nplurals=%(nplurals)d; plural=%(pluralexpr)s\n"
)


def createMessageIDSighting(messageSet, messageID):
    """Creates in the database a new message ID sighting.

    Returns None.
    """

    POMessageIDSighting(
        poMessageSet=messageSet,
        poMessageID_=messageID,
        dateFirstSeen=nowUTC,
        dateLastSeen=nowUTC,
        inLastRevision=True,
        pluralForm=0)


def createMessageSetFromMessageID(poTemplate, messageID, poFile=None):
    """Creates in the database a new message set.

    As a side-effect, creates a message ID sighting in the database for the
    new set's prime message ID.

    Returns that message set.
    """
    messageSet = POMessageSet(
        poTemplateID=poTemplate.id,
        poFile=poFile,
        primeMessageID_=messageID,
        sequence=0,
        isComplete=False,
        obsolete=False,
        fuzzy=False,
        commentText='',
        fileReferences='',
        sourceComment='',
        flagsComment='')

    createMessageIDSighting(messageSet, messageID)

    return messageSet


def createMessageSetFromText(potemplate_or_pofile, text):
    context = potemplate_or_pofile

    if isinstance(text, unicode):
        text = text.encode('utf-8')

    try:
        messageID = POMessageID.byMsgid(text)
        if context.hasMessageID(messageID):
            raise KeyError(
                "There is already a message set for this template, file and "
                "primary msgid")

    except SQLObjectNotFound:
        # If there are no existing message ids, create a new one.
        # We do not need to check whether there is already a message set
        # with the given text in this template.
        messageID = POMessageID(msgid=text)

    return context.createMessageSetFromMessageID(messageID)


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
        languages = getUtility(interfaces.ILanguageSet)

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

        # This method used to accept 'text' parameters being string ojbects,
        # but this is depracated.
        if not isinstance(text, unicode):
            raise TypeError("Message ID text must be unicode.")

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


class POTemplate(SQLBase):
    implements(interfaces.IEditPOTemplate)

    _table = 'POTemplate'

    _columns = [
        ForeignKey(name='product', foreignKey='Product', dbName='product',
            notNull=True),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
        StringCol(name='path', dbName='path', notNull=True),
        BoolCol(name='isCurrent', dbName='iscurrent', notNull=True),
        DateTimeCol(name='dateCreated', dbName='datecreated'),
        StringCol(name='copyright', dbName='copyright'),
        ForeignKey(name='branch', foreignKey='Branch', dbName='branch',
                   notNull=True),
        IntCol(name='messageCount', dbName='messagecount', notNull=True),
        IntCol(name='priority', dbName='priority', notNull=True),
        # XXX cheating, as we don't yet have classes for these
        IntCol(name='license', dbName='license', notNull=True),
    ]

    _poFilesJoin = MultipleJoin('POFile', joinColumn='potemplate')

    def poFiles(self):
        return iter(self._poFilesJoin)

    def languages(self):
        '''This returns the set of languages for which we have
        POFiles for this POTemplate. NOTE that variants are simply
        ignored, if we have three variants for en_GB we will simply
        return a single record for en_GB.

        XXX NEED DISTINCT=TRUE'''
        return Set(Language.select('''
            POFile.language = Language.id AND
            POFile.potemplate = %d
            ''' % self.id, clauseTables=('POFile', 'Language')))

    def poFile(self, language_code, variant=None):
        if variant is None:
            variantspec = 'IS NULL'
        else:
            variantspec = (u'= "%s"' % quote(variant)).encode('utf-8')

        ret = POFile.select("""
            POFile.potemplate = %d AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            """ % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=('Language',))

        if ret.count() == 0:
            raise KeyError, language_code
        else:
            return ret[0]

    def currentMessageSets(self):
        return POMessageSet.select(
            '''
            POMsgSet.potemplate = %d AND
            POMsgSet.pofile IS NULL AND
            POMsgSet.sequence > 0
            '''
            % self.id, orderBy='sequence')

    def __iter__(self):
            return iter(self.currentMessageSets())

    def __len__(self):
        '''Return the number of CURRENT MessageSets in this POTemplate.'''
        # XXX: Should we use the cached value POTemplate.messageCount instead?
        return self.currentMessageSets().count()

    def messageSet(self, key, onlyCurrent=False):
        query = '''potemplate = %d AND pofile is NULL''' % self.id
        if onlyCurrent:
            query += ' AND sequence > 0'

        if isinstance(key, slice):
            return POMessageSet.select(query, orderBy='sequence')[key]

        if not isinstance(key, unicode):
            raise TypeError(
                "Can't index with type %s. (Must be slice or unicode.)"
                    % type(key))

        # Find a message ID with the given text.
        try:
            messageID = POMessageID.byMsgid(key)
        except SQLObjectNotFound:
            raise KeyError, key

        # Find a message set with the given message ID.

        results = POMessageSet.select(query +
            (' AND primemsgid = %d' % messageID.id))

        if results.count() == 0:
            raise KeyError, key
        else:
            assert results.count() == 1

            return results[0]

    # XXX: currentCount, updatesCount and rosettaCount should be updated with
    # a way that let's us query the database instead of use the cached value

    def currentCount(self, language):
        try:
            return self.poFile(language).currentCount
        except KeyError:
            return 0

    def updatesCount(self, language):
        try:
            return self.poFile(language).updatesCount
        except KeyError:
            return 0

    def rosettaCount(self, language):
        try:
            return self.poFile(language).rosettaCount
        except KeyError:
            return 0

    def hasMessageID(self, messageID):
        results = POMessageSet.selectBy(
            poTemplateID=self.id,
            poFileID=None,
            primeMessageID_ID=messageID.id)

        return results.count() > 0

    def hasPluralMessage(self):
        results = POMessageIDSighting.select('''
            pluralform = 1 AND
            pomsgset IN (SELECT id FROM POMsgSet WHERE potemplate = %d)
            ''' % self.id)

        return results.count() > 0

    def __getitem__(self, key):
        return self.messageSet(key, onlyCurrent=True)

    # IEditPOTemplate

    def expireAllMessages(self):
        self._connection.query('UPDATE POMsgSet SET sequence = 0'
                               ' WHERE potemplate = %d AND pofile IS NULL'
                               % self.id)

    def newPOFile(self, person, language_code, variant=None):
        try:
            self.poFile(language_code, variant)
        except KeyError:
            pass
        else:
            raise KeyError(
                "This template already has a POFile for %s variant %s" %
                (language.englishName, variant))

        try:
            language = Language.byCode(language_code)
        except SQLObjectNotFound:
            raise ValueError, "Unknown language code '%s'" % language_code

        now = datetime.now()
        data = {
            'year': now.year,
            'languagename': language.englishName,
            'languagecode': language_code,
            'productname': self.product.title,
            'date': now.isoformat(' '),
            # XXX: This is not working and I'm not able to fix it easily
            #'templatedate': self.dateCreated.gmtime().Format('%Y-%m-%d %H:%M+000'),
            'templatedate': self.dateCreated,
            'copyright': self.copyright,
            'nplurals': language.pluralForms or 1,
            'pluralexpr': language.pluralExpression or '0',
            }

        return POFile(poTemplate=self,
                      language=language,
                      headerFuzzy=True,
                      title='%(languagename)s translation for %(productname)s' % data,
                      description="", # XXX: fill it
                      topComment=standardPOFileTopComment % data,
                      header=standardPOFileHeader % data,
                      lastTranslator=person,
                      currentCount=0,
                      updatesCount=0,
                      rosettaCount=0,
                      owner=person,
                      lastParsed=nowUTC,
                      pluralForms=data['nplurals'],
                      variant=variant)

    def createMessageSetFromMessageID(self, messageID):
        return createMessageSetFromMessageID(self, messageID)

    def createMessageSetFromText(self, text):
        return createMessageSetFromText(self, text)


class POFile(SQLBase):
    implements(interfaces.IEditPOFile)

    _table = 'POFile'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='POTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='language', foreignKey='Language', dbName='language',
            notNull=True),
        StringCol(name='variant', dbName='variant'),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner'),
        StringCol(name='title', dbName='title', notNull=True, unique=True),
        StringCol(name='description', dbName='description', notNull=True),
        StringCol(name='topComment', dbName='topcomment', notNull=True),
        StringCol(name='header', dbName='header', notNull=True),
        BoolCol(name='headerFuzzy', dbName='fuzzyheader', notNull=True),
        IntCol(name='currentCount', dbName='currentcount',
            notNull=True),
        IntCol(name='updatesCount', dbName='updatescount',
            notNull=True),
        IntCol(name='rosettaCount', dbName='rosettacount',
            notNull=True),
        IntCol(name='pluralForms', dbName='pluralforms', notNull=True),
        ForeignKey(name='lastTranslator', foreignKey='Person', dbName='lasttranslator'),
        DateTimeCol(name='lastParsed', dbName='lastparsed'),
        # XXX: missing fields
    ]

    messageSets = MultipleJoin('POMessageSet', joinColumn='pofile')

    def currentMessageSets(self):
        return POMessageSet.select(
            '''
            POMsgSet.pofile = %d AND
            POMsgSet.sequence > 0
            '''
            % self.id, orderBy='sequence')

    def __iter__(self):
        return iter(self.currentMessageSets())

    def __len__(self):
        '''Count of __iter__.'''
        return self.currentMessageSets().count()

    def __getitem__(self, msgid_text):
        # XXX: This is suspect. First, encoding at this layer is probably
        # unneccessary. Secondly, I'm not sure whether we should be indexing
        # by anything other than unicode messages.
        if isinstance(msgid_text, unicode):
            msgid_text = msgid_text.encode('utf-8')

        # Find the message ID object for the given text.

        try:
            msgid = POMessageID.byMsgid(msgid_text)
        except SQLObjectNotFound:
            raise KeyError, msgid_text

        # Find message sets in the PO file with the found message ID.

        results = POMessageSet.select('''
            pofile = %d AND
            primemsgid = %d
            ''' % (self.id, msgid.id))

        if results.count() == 0:
            raise KeyError, msgid_text
        elif results.count() == 1:
            return results[0]
        else:
            raise AssertionError("Duplicate message ID in PO file.")

    def translated(self):
        return iter(POMessageSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.iscomplete=TRUE AND
            POMsgSet.primemsgid = potset.primemsgid AND
            POMsgSet.potemplate = potset.potemplate AND
            potSet.pofile IS NULL AND
            potSet.sequence <> 0''' % self.id,
            clauseTables = [
                'POMsgSet potSet',
                ]))

    # XXX: This is implemented using the cache, we should add an option to get
    # the real count.
    # The number of translated are the ones from the .po file + the ones that
    # are only translated in Rosetta.

    def translatedCount(self):
        '''Returns the cached count of translated strings where translations
        exist in the files or in the database.'''
        return self.currentCount + self.rosettaCount

    def untranslated(self):
        '''XXX'''
        raise NotImplementedError

    # XXX: This is implemented using the cache, we should add an option to get
    # the real count.
    # The number of untranslated are the ones from the .pot file - the ones
    # that we have already translated.

    def untranslatedCount(self):
        '''Same as untranslated(), but with COUNT.'''
        return len(self.poTemplate) - self.translatedCount()

    def messageSetsNotInTemplate(self):
        # This is rather complex because it's actually two queries that
        # have to be added together - if someone with more sql zen knows
        # how to do it in one query, feel free to refactor.

        seqzero = POMessageSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.primemsgid = potset.primemsgid AND
            POMsgSet.potemplate = potset.potemplate AND
            potSet.pofile IS NULL AND
            POMsgSet.sequence <> 0 AND
            potSet.sequence = 0''' % self.id,
            clauseTables = [
                'POMsgSet potSet',
                ])
        notinpot = POMessageSet.select('''
            pofile = %d AND
            sequence <> 0 AND
            NOT EXISTS (
                SELECT * FROM POMsgSet potSet WHERE
                potSet.pofile IS NULL AND
                potSet.primemsgid = pomsgset.primemsgid
            )''' % self.id)

        return iter(list(seqzero) + list(notinpot))

    # IEditPOFile

    def expireAllMessages(self):
        self._connection.query(
            '''UPDATE POMsgSet SET sequence = 0 WHERE pofile = %d'''
            % self.id)

    def hasMessageID(self, messageID):
        results = POMessageSet.selectBy(
            poTemplateID=self.poTemplate.id,
            poFileID=self.id,
            primeMessageID_ID=messageID.id)

        return results.count() > 0

    def createMessageSetFromMessageID(self, messageID):
        return createMessageSetFromMessageID(self.poTemplate, messageID, self)

    def createMessageSetFromText(self, text):
        return createMessageSetFromText(self, text)

    def updateStatistics(self):
        # XXX: Carlos Perello Marin 05/10/04 This method should be reviewed
        # harder after the final decission about how should we use active and
        # inLastRevision fields.
        # I'm not doing it now because the statistics works is not completed
        # and I don't want to conflict with lalo's work.
        current = POMessageSet.select('''
            POMsgSet.sequence > 0 AND
            POMsgSet.fuzzy = FALSE AND
            PotSet.sequence > 0 AND
            PotSet.primeMsgID = POMsgSet.primeMsgID AND
            POMsgSet.pofile = %d AND
            PotSet.potemplate = POMsgSet.potemplate
            ''' % self.id, clauseTables=('POMsgSet PotSet',)).count()
        updates = POMessageSet.select('''
            POMsgSet.sequence > 0 AND
            POMsgSet.fuzzy = FALSE AND
            PotSet.sequence > 0 AND
            PotSet.primeMsgID = POMsgSet.primeMsgID AND
            POMsgSet.pofile = %d AND
            PotSet.potemplate = POMsgSet.potemplate AND
            FileSighting.pomsgset = POMsgSet.id AND
            RosettaSighting.pomsgset = POMsgSet.id AND
            FileSighting.inLastRevision = TRUE AND
            RosettaSighting.inLastRevision = FALSE AND
            FileSighting.active = TRUE AND
            RosettaSighting.active = TRUE AND
            RosettaSighting.dateLastActive > FileSighting.dateLastActive
            ''' % self.id, clauseTables=(
                                         'POMsgSet PotSet',
                                         'POTranslationSighting FileSighting',
                                         'POTranslationSighting RosettaSighting',
                                        )).count()
        rosetta = POMessageSet.select('''
            POMsgSet.fuzzy = FALSE AND
            PotSet.sequence > 0 AND
            PotSet.primeMsgID = POMsgSet.primeMsgID AND
            POMsgSet.pofile = %d AND
            PotSet.potemplate = POMsgSet.potemplate AND
            PotSet.pofile IS NULL AND
            (SELECT COUNT(*) from
              POTranslationSighting POSighting WHERE
              POSighting.POMsgSet = POMsgSet.id AND
              POSighting.active = TRUE AND
              POSighting.inLastRevision = TRUE) = 0 AND
            (SELECT COUNT(*) from
              POTranslationSighting RosettaSighting WHERE
              RosettaSighting.POMsgSet = POMsgSet.id AND
              RosettaSighting.active = TRUE) > 0
            ''' % self.id, clauseTables=(
                                         'POMsgSet PotSet',
                                        )).count()
        self.set(currentCount=current,
                 updateCount=updates,
                 rosettaCount=rosetta)
        return (current, updates, rosetta)


class POMessageIDSighting(SQLBase):
    implements(interfaces.IPOMessageIDSighting)

    _table = 'POMsgIDSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='POMessageSet', dbName='pomsgset', notNull=True),
        ForeignKey(name='poMessageID_', foreignKey='POMessageID', dbName='pomsgid', notNull=True),
        DateTimeCol(name='dateFirstSeen', dbName='datefirstseen', notNull=True),
        DateTimeCol(name='dateLastSeen', dbName='datelastseen', notNull=True),
        BoolCol(name='inLastRevision', dbName='inlastrevision', notNull=True),
        IntCol(name='pluralForm', dbName='pluralform', notNull=True),
    ]


class POMessageID(SQLBase):
    implements(interfaces.IPOMessageID)

    _table = 'POMsgID'

    _columns = [
        StringCol(name='msgid', dbName='msgid', notNull=True, unique=True,
            alternateID=True)
    ]


class POTranslationSighting(SQLBase):
    implements(interfaces.IPOTranslationSighting)

    _table = 'POTranslationSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='POMessageSet',
            dbName='pomsgset', notNull=True),
        ForeignKey(name='poTranslation', foreignKey='POTranslation',
            dbName='potranslation', notNull=True),
        ForeignKey(name='person', foreignKey='Person',
            dbName='person', notNull=True),
        DateTimeCol(name='dateFirstSeen', dbName='datefirstseen', notNull=True),
        DateTimeCol(name='dateLastActive', dbName='datelastactive', notNull=True),
        BoolCol(name='inLastRevision', dbName='inlastrevision', notNull=True),
        IntCol(name='pluralForm', dbName='pluralform', notNull=True),
        # See canonical.lp.dbschema.RosettaTranslationOrigin.
        IntCol(name='origin', dbName='origin', notNull=True),
        BoolCol(name='active', dbName='active', notNull=True),
        # XXX cheating, as we don't yet have classes for these
        IntCol(name='license', dbName='license', notNull=True),
    ]


class POTranslation(SQLBase):
    implements(interfaces.IPOTranslation)

    _table = 'POTranslation'

    _columns = [
        StringCol(name='translation', dbName='translation', notNull=True,
            unique=True, alternateID=True)
    ]


