# arch-tag: da5d31ba-6994-4893-b252-83f4f66f0aba
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


class Languages(object):
    implements(interfaces.ILanguages)

    def __iter__(self):
        return iter(Language.select(orderBy='englishName'))

    def __getitem__(self, code):
        try:
            return Language.byCode(code)
        except SQLObjectNotFound:
            raise KeyError, code

    def keys(self):
        return [language.code for language in Language.select()]


class Language(SQLBase):
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
            schema = Schema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        return Label.selectBy(schemaID=schema.id, name=self.code)

    def translators(self):
        return self.translateLabel().persons()


def personFromPrincipal(principal):
    from zope.app.security.interfaces import IUnauthenticatedPrincipal
    from canonical.lp.placelessauth.launchpadsourceutility import \
        LaunchpadPrincipal

    if IUnauthenticatedPrincipal.providedBy(principal):
        return None

    if not isinstance(principal, LaunchpadPrincipal):
        return None

    return Person.get(principal.id)


class Schemas(object):
    implements(interfaces.ISchemas)

    def __getitem__(self, name):
        try:
            schema = Schema.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name
        else:
            return schema

    def keys(self):
        return [schema.name for schema in Schema.select()]


class Schema(SQLBase):
    implements(interfaces.ISchema)

    _table = 'Schema'

    _columns = [
        ForeignKey(name='owner', foreignKey='Person',
            dbName='owner', notNull=True),
        StringCol(name='name', dbName='name', notNull=True, alternateID=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
#        BoolCol(name='extensible', dbName='extensible', notNull=True),
    ]

    _labelsJoin = MultipleJoin('Label', joinColumn='schema')

    def labels(self):
        return iter(self._labelsJoin)

    def label(self, name):
        '''SELECT * FROM Label WHERE
            Label.schema = id AND
            Label.name = name;'''
        results = Label.select('''
            Label.schema = %d AND
            Label.name = %s''' %
            (self.id, quote(name)))

        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]


class Label(SQLBase):
    implements(interfaces.ILabel)

    _table = 'Label'

    _columns = [
        ForeignKey(name='schema', foreignKey='Schema', dbName='schema',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
    ]

    _personsJoin = RelatedJoin('Person', joinColumn='label',
        otherColumn='person', intermediateTable='PersonLabel')

    def persons(self):
        for person in self._personsJoin:
            yield person[0]


class Category(Label):
    implements(interfaces.ICategory)

    _effortPOTemplatesJoin = MultipleJoin('TranslationEffortPOTemplate',
        joinColumn='category')

    def poTemplates(self):
        # XXX: We assume that template will have always a row because the
        # database's referencial integrity
        for effortPOTemplate in self._effortPOTemplatesJoin:
            template = POTemplate.selectBy(id=effortPOTemplate.poTemplate)
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


class TranslationEfforts(object):
    implements(interfaces.ITranslationEfforts)

    def __iter__(self):
        return iter(TranslationEffort.select())

    def __getitem__(self, name):
        ret = TranslationEffort.selectBy(name=name)

        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

    def new(self, name, title, shortDescription, description, owner, project):
        if TranslationEffort.selectBy(name=name).count():
            raise KeyError, "There is already a translation effort with that name"

        return TranslationEffort(name=name,
                              title=title,
                              shortDescription=shortDescription,
                              description=description,
                              owner=owner, project=project)

    def search(self, query):
        query = quote('%%' + query + '%%')
        #query = quote(query)
        return TranslationEffort.select('''title ILIKE %s  OR description ILIKE %s''' %
            (query, query))


class TranslationEffort(SQLBase):
    implements(interfaces.ITranslationEffort)

    _table = 'TranslationEffort'

    _columns = [
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
            notNull=True),
        ForeignKey(name='project', foreignKey='Project',
            dbName='project', notNull=True),
        ForeignKey(name='categoriesSchema', foreignKey='Schema',
            dbName='categories', notNull=False),
        StringCol(name='name', dbName='name', notNull=True, unique=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='shortDescription', dbName='shortdesc', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
    ]

    def categories(self):
        '''SELECT * FROM Label
            WHERE schema=self.categories'''
        return iter(Category.selectBy(schema=self.categories))

    def category(self, name):
        ret = Category.selectBy(name=name, schema=self.categories)

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


class TranslationEffortPOTemplate(SQLBase):
    implements(interfaces.ITranslationEffortPOTemplate)

    _table = 'TranslationEffortPOTemplate'

    _columns = [
        ForeignKey(name='translationEffort',
            foreignKey='TranslationEffort', dbName='translationeffort',
            notNull=True),
        ForeignKey(name='poTemplate', foreignKey='POTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='category', foreignKey='Category',
            dbName='category', notNull=False),
        IntCol(name='priority', dbName='priority', notNull=True),
    ]


################################################################################
# And now the ones that conflict

class RosettaEmailAddress(SQLBase):
    implements(interfaces.IEmailAddress)

    _table = 'EmailAddress'

    _columns = [
        ForeignKey(name='person', foreignKey='Person', dbName='person',
            notNull=True),
        StringCol(name='email', dbName='email', notNull=True, unique=True),
        IntCol(name='status', dbName='status', notNull=True),
    ]
