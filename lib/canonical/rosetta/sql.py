# arch-tag: da5d31ba-6994-4893-b252-83f4f66f0aba

from canonical.database.sqlbase import SQLBase, quote

import canonical.rosetta.interfaces as interfaces
from canonical.database.doap import IProject, IProjectSet
from canonical.database.constants import nowUTC

from sqlobject import ForeignKey, MultipleJoin, RelatedJoin, IntCol, \
    BoolCol, StringCol, DateTimeCol, SQLObjectNotFound
from zope.interface import implements, directlyProvides
from zope.component import getUtility
from canonical.rosetta import pofile
from types import NoneType
from datetime import datetime
from sets import Set

standardTemplateCopyright = 'Canonical Ltd'

# XXX: in the four strings below, we should fill in owner information
standardTemplateTopComment = ''' PO template for %(productname)s
 Copyright (c) %(copyright)s %(year)s
 This file is distributed under the same license as the %(productname)s package.
 PROJECT MAINTAINER OR MAILING LIST <EMAIL@ADDRESS>, %(year)s.

'''

# XXX: project-id-version needs a version
standardTemplateHeader = (
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


class RosettaProduct(SQLBase):
    implements(interfaces.IProduct)

    _table = 'Product'

    _columns = [
        ForeignKey(name='project', foreignKey='Project', dbName='project',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True, unique=True),
        StringCol(name='displayName', dbName='displayname', notNull=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='shortDesc', dbName='shortdesc', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
        ForeignKey(name='owner', foreignKey='RosettaPerson', dbName='owner',
            notNull=True),
        StringCol(name='url', dbName='homepageurl')
    ]

    _poTemplatesJoin = MultipleJoin('RosettaPOTemplate', joinColumn='product')

    def poTemplates(self):
        return iter(self._poTemplatesJoin)

    def poTemplate(self, name):
        '''SELECT POTemplate.* FROM POTemplate WHERE
            POTemplate.product = id AND
            POTemplate.name = name;'''
        results = RosettaPOTemplate.select('''
            POTemplate.product = %d AND
            POTemplate.name = %s''' %
            (self.id, quote(name)))

        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]

    def newPOTemplate(self, person, name, title):
        # XXX: we have to fill up a lot of other attributes
        if RosettaPOTemplate.selectBy(
                productID=self.id, name=name).count():
            raise KeyError(
                  "This product already has a template named %s" % name)
        return RosettaPOTemplate(name=name, title=title, product=self)

    def messageCount(self):
        count = 0
        for t in self.poTemplates():
            count += len(t)
        return count

    def currentCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.currentCount(language)
        return count

    def updatesCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.updatesCount(language)
        return count

    def rosettaCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.rosettaCount(language)
        return count


def createMessageIDSighting(messageSet, messageID):
    """Creates in the database a new message ID sighting.

    Returns None.
    """

    RosettaPOMessageIDSighting(
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
    messageSet = RosettaPOMessageSet(
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
        messageID = RosettaPOMessageID.byMsgid(text)
        if context.hasMessageID(messageID):
            raise KeyError(
                "There is already a message set for this template, file and "
                "primary msgid")
                
    except SQLObjectNotFound:
        # If there are no existing message ids, create a new one.
        # We do not need to check whether there is already a message set
        # with the given text in this template.
        messageID = RosettaPOMessageID(msgid=text)
        
    return context.createMessageSetFromMessageID(messageID)


class RosettaPOTemplate(SQLBase):
    implements(interfaces.IEditPOTemplate)

    _table = 'POTemplate'

    _columns = [
        ForeignKey(name='product', foreignKey='RosettaProduct', dbName='product',
            notNull=True),
        ForeignKey(name='owner', foreignKey='RosettaPerson', dbName='owner'),
        StringCol(name='name', dbName='name', notNull=True, unique=True),
        StringCol(name='title', dbName='title', notNull=True, unique=True),
        StringCol(name='description', dbName='description', notNull=True),
        StringCol(name='path', dbName='path', notNull=True),
        BoolCol(name='isCurrent', dbName='iscurrent', notNull=True),
        DateTimeCol(name='dateCreated', dbName='datecreated'),
        StringCol(name='copyright', dbName='copyright'),
        ForeignKey(name='branch', foreignKey='RosettaBranch', dbName='branch',
                   notNull=True),
        IntCol(name='messageCount', dbName='messagecount', notNull=True),
        IntCol(name='priority', dbName='priority', notNull=True),
        # XXX cheating, as we don't yet have classes for these
        IntCol(name='license', dbName='license', notNull=True),
    ]

    _poFilesJoin = MultipleJoin('RosettaPOFile', joinColumn='potemplate')

    def poFiles(self):
        return iter(self._poFilesJoin)

    def languages(self):
        '''This returns the set of languages for which we have
        POFiles for this POTemplate. NOTE that variants are simply
        ignored, if we have three variants for en_GB we will simply
        return a single record for en_GB.

        XXX NEED DISTINCT=TRUE'''
        return Set(RosettaLanguage.select('''
            POFile.language = Language.id AND
            POFile.potemplate = %d
            ''' % self.id, clauseTables=('POFile', 'Language')))

    def poFile(self, language_code, variant=None):
        if variant is None:
            variantspec = 'IS NULL'
        else:
            variantspec = (u'= "%s"' % quote(variant)).encode('utf-8')

        ret = RosettaPOFile.select("""
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
        return RosettaPOMessageSet.select(
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
            return RosettaPOMessageSet.select(query, orderBy='sequence')[key]

        if not isinstance(key, unicode):
            raise TypeError(
                "Can't index with type %s. (Must be slice or unicode.)"
                    % type(key))

        # Find a message ID with the given text.
        try:
            messageID = RosettaPOMessageID.byMsgid(key)
        except SQLObjectNotFound:
            raise KeyError, key

        # Find a message set with the given message ID.

        results = RosettaPOMessageSet.select(query +
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
        results = RosettaPOMessageSet.selectBy(
            poTemplateID=self.id,
            poFileID=None,
            primeMessageID_ID=messageID.id)

        return results.count() > 0

    def hasPluralMessage(self):
        results = RosettaPOMessageIDSighting.select('''
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
            language = RosettaLanguage.byCode(language_code)
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

        return RosettaPOFile(poTemplate=self,
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


class RosettaPOFile(SQLBase):
    implements(interfaces.IEditPOFile)

    _table = 'POFile'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='RosettaPOTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='language', foreignKey='RosettaLanguage', dbName='language',
            notNull=True),
        StringCol(name='variant', dbName='variant'),
        ForeignKey(name='owner', foreignKey='RosettaPerson', dbName='owner'),
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
        ForeignKey(name='lastTranslator', foreignKey='RosettaPerson', dbName='lasttranslator'),
        DateTimeCol(name='lastParsed', dbName='lastparsed'),
        # XXX: missing fields
    ]

    messageSets = MultipleJoin('RosettaPOMessageSet', joinColumn='pofile')

    def currentMessageSets(self):
        return RosettaPOMessageSet.select(
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
            msgid = RosettaPOMessageID.byMsgid(msgid_text)
        except SQLObjectNotFound:
            raise KeyError, msgid_text

        # Find message sets in the PO file with the found message ID.

        results = RosettaPOMessageSet.select('''
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
        return iter(RosettaPOMessageSet.select('''
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

        seqzero = RosettaPOMessageSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.primemsgid = potset.primemsgid AND
            POMsgSet.potemplate = potset.potemplate AND
            potSet.pofile IS NULL AND
            POMsgSet.sequence <> 0 AND
            potSet.sequence = 0''' % self.id,
            clauseTables = [
                'POMsgSet potSet',
                ])
        notinpot = RosettaPOMessageSet.select('''
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
        results = RosettaPOMessageSet.selectBy(
            poTemplateID=self.poTemplate.id,
            poFileID=self.id,
            primeMessageID_ID=messageID.id)

        return results.count() > 0

    def createMessageSetFromMessageID(self, messageID):
        return createMessageSetFromMessageID(self.poTemplate, messageID, self)

    def createMessageSetFromText(self, text):
        return createMessageSetFromText(self, text)

    def updateStatistics(self):
        current = RosettaPOMessageSet.select('''
            POMsgSet.sequence > 0 AND
            POMsgSet.fuzzy = FALSE AND
            PotSet.sequence > 0 AND
            PotSet.primeMsgID = POMsgSet.primeMsgID AND
            POMsgSet.pofile = %d AND
            PotSet.potemplate = POMsgSet.potemplate
            ''' % self.id, clauseTables=('POMsgSet PotSet',)).count()
        updates = RosettaPOMessageSet.select('''
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
        rosetta = RosettaPOMessageSet.select('''
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


class RosettaPOMessageSet(SQLBase):
    implements(interfaces.IEditPOTemplateOrPOFileMessageSet)

    _table = 'POMsgSet'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='RosettaPOTemplate', dbName='potemplate', notNull=True),
        ForeignKey(name='poFile', foreignKey='RosettaPOFile', dbName='pofile', notNull=False),
        ForeignKey(name='primeMessageID_', foreignKey='RosettaPOMessageID', dbName='primemsgid', notNull=True),
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
        return RosettaPOMessageID.select('''
            POMsgIDSighting.pomsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id AND
            POMsgIDSighting.inlastrevision = TRUE
            ''' % self.id, clauseTables=('POMsgIDSighting',),
            orderBy='POMsgIDSighting.pluralform')

    def getMessageIDSighting(self, pluralForm, allowOld=False):
        """Return the message ID sighting that is current and has the
        plural form provided."""
        if allowOld:
            results = RosettaPOMessageIDSighting.selectBy(
                poMessageSetID=self.id,
                pluralForm=pluralForm)
        else:
            results = RosettaPOMessageIDSighting.selectBy(
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

        potset = RosettaPOMessageSet.select('''
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

        results = list(RosettaPOTranslationSighting.select(
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

        results = RosettaPOMessageSet.select('''pofile = %d AND primemsgid = %d'''
            % (pofile.id, self.primeMessageID_.id))

        if not (0 <= results.count() <= 1):
            raise AssertionError("Duplicate message ID in PO file.")

        if results.count() == 0:
            return [None] * pluralforms

        translation_set = results[0]

        results = list(RosettaPOTranslationSighting.select(
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
            translations = RosettaPOTranslationSighting.selectBy(
                poMessageSetID=self.id,
                pluralForm=pluralForm)
        else:
            translations = RosettaPOTranslationSighting.selectBy(
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
        return RosettaPOTranslationSighting.selectBy(
            poMessageSetID=self.id)

    # IEditPOMessageSet

    def makeMessageIDSighting(self, text, pluralForm, update=False):
        """Create a new message ID sighting for this message set."""

        if type(text) is unicode:
            text = text.encode('utf-8')

        try:
            messageID = RosettaPOMessageID.byMsgid(text)
        except SQLObjectNotFound:
            messageID = RosettaPOMessageID(msgid=text)

        existing = RosettaPOMessageIDSighting.selectBy(
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
            # XXX: Do we always want to set inLastRevision to True?
            existing.set(dateLastSeen = nowUTC, inLastRevision = True)

            return existing

        return RosettaPOMessageIDSighting(
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

        # First get hold of a RosettaPOTranslation for the specified text.
        try:
            translation = RosettaPOTranslation.byTranslation(text)
        except SQLObjectNotFound:
            translation = RosettaPOTranslation(translation=text)

        # Now get hold of any existing translation sightings.

        results = RosettaPOTranslationSighting.selectBy(
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
                inLastRevision = sighting.inLastRevision or fromPOFile)
        else:
            # No sighting exists yet.

            # XXX: This should use dbschema constants.
            if fromPOFile:
                origin = 1
            else:
                origin = 2

            sighting = RosettaPOTranslationSighting(
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


class RosettaPOMessageIDSighting(SQLBase):
    implements(interfaces.IPOMessageIDSighting)

    _table = 'POMsgIDSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='RosettaPOMessageSet', dbName='pomsgset', notNull=True),
        ForeignKey(name='poMessageID_', foreignKey='RosettaPOMessageID', dbName='pomsgid', notNull=True),
        DateTimeCol(name='dateFirstSeen', dbName='datefirstseen', notNull=True),
        DateTimeCol(name='dateLastSeen', dbName='datelastseen', notNull=True),
        BoolCol(name='inLastRevision', dbName='inlastrevision', notNull=True),
        IntCol(name='pluralForm', dbName='pluralform', notNull=True),
    ]


class RosettaPOMessageID(SQLBase):
    implements(interfaces.IPOMessageID)

    _table = 'POMsgID'

    _columns = [
        StringCol(name='msgid', dbName='msgid', notNull=True, unique=True,
            alternateID=True)
    ]


class RosettaPOTranslationSighting(SQLBase):
    implements(interfaces.IPOTranslationSighting)

    _table = 'POTranslationSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='RosettaPOMessageSet',
            dbName='pomsgset', notNull=True),
        ForeignKey(name='poTranslation', foreignKey='RosettaPOTranslation',
            dbName='potranslation', notNull=True),
        ForeignKey(name='person', foreignKey='RosettaPerson',
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


class RosettaPOTranslation(SQLBase):
    implements(interfaces.IPOTranslation)

    _table = 'POTranslation'

    _columns = [
        StringCol(name='translation', dbName='translation', notNull=True,
            unique=True, alternateID=True)
    ]


class RosettaLanguages(object):
    implements(interfaces.ILanguages)

    def __iter__(self):
        return iter(RosettaLanguage.select(orderBy='englishName'))

    def __getitem__(self, code):
        try:
            return RosettaLanguage.byCode(code)
        except SQLObjectNotFound:
            raise KeyError, code

    def keys(self):
        return [language.code for language in RosettaLanguage.select()]


class RosettaLanguage(SQLBase):
    implements(interfaces.ILanguage)

    _table = 'Language'

    _columns = [
        StringCol(name='code', dbName='code', notNull=True, unique=True,
            alternateID=True),
        StringCol(name='nativeName', dbName='nativename'),
        StringCol(name='englishName', dbName='englishname'),
        IntCol(name='pluralForms', dbName='pluralforms'),
        StringCol(name='pluralExpression', dbName='pluralexpression'),
    ]

    def translateLabel(self):
        try:
            schema = RosettaSchema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        return RosettaLabel.selectBy(schemaID=schema.id, name=self.code)

    def translators(self):
        return self.translateLabel().persons()


class RosettaPerson(SQLBase):
    implements(interfaces.IPerson)

    _table = 'Person'

    _columns = [
        StringCol(name='displayName', dbName='displayname'),
        StringCol(name='givenName', dbName='givenname'),
        StringCol(name='familyName', dbName='familyname'),
        StringCol(name='password', dbName='password'),
    ]

#    isMaintainer
#    isTranslator
#    isContributor

    # Invariant: isMaintainer implies isContributor

    _emailsJoin = MultipleJoin('RosettaEmailAddress', joinColumn='person')

    def emails(self):
        return iter(self._emailsJoin)

    # XXX: not implemented
    def maintainedProjects(self):
        '''SELECT Project.* FROM Project
            WHERE Project.owner = self.id
            '''

    # XXX: not implemented
    def translatedProjects(self):
        '''SELECT Project.* FROM Project, Product, POTemplate, POFile
            WHERE
                POFile.owner = self.id AND
                POFile.template = POTemplate.id AND
                POTemplate.product = Product.id AND
                Product.project = Project.id
            ORDER BY ???
            '''

    def translatedTemplates(self):
        '''
        SELECT * FROM POTemplate WHERE
            id IN (SELECT potemplate FROM pomsgset WHERE
                id IN (SELECT pomsgset FROM POTranslationSighting WHERE
                    origin = 2
                ORDER BY datefirstseen DESC))
        '''
        return RosettaPOTemplate.select('''
            id IN (SELECT potemplate FROM pomsgset WHERE
                id IN (SELECT pomsgset FROM POTranslationSighting WHERE
                    origin = 2
                ORDER BY datefirstseen DESC))
            ''')

    _labelsJoin = RelatedJoin('RosettaLabel', joinColumn='person',
        otherColumn='label', intermediateTable='PersonLabel')

    def languages(self):
        languages = getUtility(interfaces.ILanguages)
        try:
            schema = RosettaSchema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")

        for label in self._labelsJoin:
            if label.schema == schema:
                yield languages[label.name]

    def addLanguage(self, language):
        try:
            schema = RosettaSchema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        label = RosettaLabel.selectBy(schemaID=schema.id, name=language.code)
        if label.count() < 1:
            # The label for this language does not exists yet into the
            # database, we should create it.
            label = RosettaLabel(
                        schemaID=schema.id,
                        name=language.code,
                        title='Translates into ' + language.englishName,
                        description='A person with this label says that ' + \
                                    'knows how to translate into ' + \
                                    language.englishName)
        # This method comes from the RelatedJoin
        self.addRosettaLabel(label)

    def removeLanguage(self, language):
        try:
            schema = RosettaSchema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        label = RosettaLabel.selectBy(schemaID=schema.id, name=language.code)[0]
        # This method comes from the RelatedJoin
        self.removeRosettaLabel(label)


class RosettaBranch(SQLBase):
    implements(interfaces.IBranch)

    _table = 'Branch'

    _columns = [
        StringCol(name='title', dbName='title'),
        StringCol(name='description', dbName='description')
    ]


def personFromPrincipal(principal):
    from zope.app.security.interfaces import IUnauthenticatedPrincipal
    from canonical.lp.placelessauth.launchpadsourceutility import \
        LaunchpadPrincipal

    if IUnauthenticatedPrincipal.providedBy(principal):
        return None

    if not isinstance(principal, LaunchpadPrincipal):
        return None

    return RosettaPerson.get(principal.id)


class RosettaSchemas(object):
    implements(interfaces.ISchemas)

    def __getitem__(self, name):
        try:
            schema = RosettaSchema.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name
        else:
            return schema

    def keys(self):
        return [schema.name for schema in RosettaSchema.select()]


class RosettaSchema(SQLBase):
    implements(interfaces.ISchema)

    _table = 'Schema'

    _columns = [
        ForeignKey(name='owner', foreignKey='RosettaPerson',
            dbName='owner', notNull=True),
        StringCol(name='name', dbName='name', notNull=True, alternateID=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
#        BoolCol(name='extensible', dbName='extensible', notNull=True),
    ]

    _labelsJoin = MultipleJoin('RosettaLabel', joinColumn='schema')

    def labels(self):
        return iter(self._labelsJoin)

    def label(self, name):
        '''SELECT * FROM Label WHERE
            Label.schema = id AND
            Label.name = name;'''
        results = RosettaLabel.select('''
            Label.schema = %d AND
            Label.name = %s''' %
            (self.id, quote(name)))

        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]


class RosettaLabel(SQLBase):
    implements(interfaces.ILabel)

    _table = 'Label'

    _columns = [
        ForeignKey(name='schema', foreignKey='RosettaSchema', dbName='schema',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
    ]

    _personsJoin = RelatedJoin('RosettaPerson', joinColumn='label',
        otherColumn='person', intermediateTable='PersonLabel')

    def persons(self):
        for person in self._personsJoin:
            yield person[0]


class RosettaCategory(RosettaLabel):
    implements(interfaces.ICategory)

    _effortPOTemplatesJoin = MultipleJoin('RosettaTranslationEffortPOTemplate',
        joinColumn='category')

    def poTemplates(self):
        # XXX: We assume that template will have always a row because the
        # database's referencial integrity
        for effortPOTemplate in self._effortPOTemplatesJoin:
            template = RosettaPOTemplate.selectBy(id=effortPOTemplate.poTemplate)
            yield template[0]

    def poTemplate(self, name):
        for template in self.poTemplates():
            if template.name == name:
                return template

        raise KeyError, name

    def messageCount(self):
        count = 0
        for t in self.poTemplates():
            count += len(t)
        return count

    def currentCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.currentCount(language)
        return count

    def updatesCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.updatesCount(language)
        return count

    def rosettaCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.rosettaCount(language)
        return count


class RosettaTranslationEfforts(object):
    implements(interfaces.ITranslationEfforts)

    def __iter__(self):
        return iter(RosettaTranslationEffort.select())

    def __getitem__(self, name):
        ret = RosettaTranslationEffort.selectBy(name=name)

        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

    def new(self, name, title, shortDescription, description, owner, project):
        if RosettaTranslationEffort.selectBy(name=name).count():
            raise KeyError, "There is already a translation effort with that name"

        return RosettaTranslationEffort(name=name,
                              title=title,
                              shortDescription=shortDescription,
                              description=description,
                              owner=owner, project=project)

    def search(self, query):
        query = quote('%%' + query + '%%')
        #query = quote(query)
        return RosettaTranslationEffort.select('''title ILIKE %s  OR description ILIKE %s''' %
            (query, query))


class RosettaTranslationEffort(SQLBase):
    implements(interfaces.ITranslationEffort)

    _table = 'TranslationEffort'

    _columns = [
        ForeignKey(name='owner', foreignKey='RosettaPerson', dbName='owner',
            notNull=True),
        ForeignKey(name='project', foreignKey='Project',
            dbName='project', notNull=True),
        ForeignKey(name='categoriesSchema', foreignKey='RosettaSchema',
            dbName='categories', notNull=False),
        StringCol(name='name', dbName='name', notNull=True, unique=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='shortDescription', dbName='shortdesc', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
    ]

    def categories(self):
        '''SELECT * FROM Label
            WHERE schema=self.categories'''
        return iter(RosettaCategory.selectBy(schema=self.categories))

    def category(self, name):
        ret = RosettaCategory.selectBy(name=name, schema=self.categories)

        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

    def messageCount(self):
        count = 0
        for c in self.categories():
            count += c.messageCount()
        return count

    def currentCount(self, language):
        count = 0
        for c in self.categories():
            count += c.currentCount(language)
        return count

    def updatesCount(self, language):
        count = 0
        for c in self.categories():
            count += c.updatesCount(language)
        return count

    def rosettaCount(self, language):
        count = 0
        for c in self.categories():
            count += c.rosettaCount(language)
        return count


class RosettaTranslationEffortPOTemplate(SQLBase):
    implements(interfaces.ITranslationEffortPOTemplate)

    _table = 'TranslationEffortPOTemplate'

    _columns = [
        ForeignKey(name='translationEffort',
            foreignKey='RosettaTranslationEffort', dbName='translationeffort',
            notNull=True),
        ForeignKey(name='poTemplate', foreignKey='RosettaPOTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='category', foreignKey='RosettaCategory',
            dbName='category', notNull=False),
        IntCol(name='priority', dbName='priority', notNull=True),
    ]

class RosettaEmailAddress(SQLBase):
    implements(interfaces.IEmailAddress)

    _table = 'EmailAddress'

    _columns = [
        ForeignKey(name='person', foreignKey='RosettaPerson', dbName='person',
            notNull=True),
        StringCol(name='email', dbName='email', notNull=True, unique=True),
        IntCol(name='status', dbName='status', notNull=True),
    ]

