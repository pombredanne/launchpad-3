# arch-tag: da5d31ba-6994-4893-b252-83f4f66f0aba

from canonical.database.sqlbase import SQLBase, quote
from canonical.rosetta.interfaces import *
from sqlobject import ForeignKey, MultipleJoin, IntCol, BoolCol, StringCol, \
    DateTimeCol
from zope.interface import implements, directlyProvides
from zope.component import getUtility
from canonical.rosetta import pofile
from types import NoneType
from datetime import datetime
from sets import Set

standardTemplateCopyright = 'Canonical Ltd'

# XXX: in the four strings below, we should fill in owner information
standardTemplateTopComment = '''# PO template for %(productname)s
# Copyright (c) %(copyright)s %(year)s
# This file is distributed under the same license as the %(productname)s package.
# PROJECT MAINTAINER OR MAILING LIST <EMAIL@ADDRESS>, %(year)s.
# 
'''

# XXX: project-id-version needs a version
standardTemplateHeader = '''msgid ""
msgstr ""
"Project-Id-Version: %(productname)s\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE NAME <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"X-Rosetta-Version: 0.1\n"
'''

standardPOFileTopComment = '''# %(languagename)s translation for %(productname)s
# Copyright (c) %(copyright)s %(year)s
# This file is distributed under the same license as the %(productname)s package.
# FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.
# 
'''

standardPOFileHeader = '''msgid ""
msgstr ""
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
'''


class RosettaProjects(object):
    implements(IProjects)

    def __iter__(self):
        return iter(RosettaProject.select())

    def __getitem__(self, name):
        ret = RosettaProject.selectBy(name=name)

        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

    def new(self, name, title, url, description, owner):
        if RosettaProject.selectBy(name=name).count():
            raise KeyError, "There is already a project with that name"

        return RosettaProject(name=name,
                              displayName=displayName,
                              title=title, url=url,
                              description=description,
                              owner=owner, datecreated='now')

    def search(self, query):
        query = quote('%%' + query + '%%')
        #query = quote(query)
        return RosettaProject.select('''title ILIKE %s  OR description ILIKE %s''' %
            (query, query))


class RosettaProject(SQLBase):
    implements(IProject)

    _table = 'Project'

    _columns = [
        ForeignKey(name='owner', foreignKey='RosettaPerson', dbName='owner',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True, unique=True),
        StringCol(name='displayName', dbName='displayName', notNull=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
        DateTimeCol(name='datecreated', dbName='datecreated', notNull=True),
        StringCol(name='url', dbName='homepageurl')
    ]

    _productsJoin = MultipleJoin('RosettaProduct', joinColumn='project')

    def products(self):
        return iter(self._productsJoin)

    def product(self, name):
        print name
        ret = RosettaProduct.selectBy(name=name)

        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

    def poTemplate(self, name):
        results = RosettaPOTemplate.selectBy(name=name)
        count = results.count()

        if count == 0:
            raise KeyError, name
        elif count > 1:
            raise ValueError, "whoops!"
        else:
            return results[0]

    def poTemplates(self):
        for p in self.products():
            for t in p.poTemplates():
                yield t

    def messageCount(self):
        count = 0
        for p in self.products():
            count += p.messageCount()
        return count

    def currentCount(self, language):
        count = 0
        for p in self.products():
            count += p.currentCount(language)
        return count

    def updatesCount(self, language):
        count = 0
        for p in self.products():
            count += p.updatesCount(language)
        return count

    def rosettaCount(self, language):
        count = 0
        for p in self.products():
            count += p.rosettaCount(language)
        return count


class RosettaProduct(SQLBase):
    implements(IProduct)

    _table = 'Product'

    _columns = [
        ForeignKey(name='project', foreignKey='RosettaProject', dbName='project',
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
        if RosettaPOTemplate.selectBy(productID=self.id,
                                      name=name).count():
            raise KeyError, \
                  "This product already has a template named %s" % name
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
        dateFirstSeen="NOW",
        dateLastSeen="NOW",
        inLastRevision=False,
        pluralForm=0)


def createMessageSetFromMessageID(poTemplate, messageID, poFile=None):
    """Creates in the database a new message set.

    As a side-effect, creates a message ID sighting in the database for the
    new set's prime message ID.

    Returns that message set.
    """
    messageSet = RosettaPOMessageSet(
        poTemplateID=potemplate.id,
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

    messageIDs = RosettaPOMessageID.selectBy(msgid=text)
    if messageIDs.count() == 0:
        # If there are no existing message ids, create a new one.
        # We do not need to check whether there is already a message set
        # with the given text in this template.
        messageID = RosettaPOMessageID(msgid=text)
    else:
        # Otherwise, use the existing one.
        assert messageIDs.count() == 1
        messageID = messageIDs[0]

        if context.hasMessageID(messageID):
            raise KeyError("There is already a message set for"
                           " this template, file and primary msgid")

    return context.createMessageSetFromMessageID(messageID)


class RosettaPOTemplate(SQLBase):
    implements(IEditPOTemplate)

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

    def __getitem__(self, key):
        if isinstance(key, slice):
            return RosettaPOMessageSet.select('''
                potemplate = %d AND
                pofile is NULL AND
                sequence > 0
                ''' % self.id)[key]

        if isinstance(key, unicode):
            text = key.encode('utf-8')
        elif isinstance(key, string):
            text = key
        else:
            raise TypeError, "Can't index with this type."

        results = RosettaPOMessageID.selectBy(msgid=text)

        if results.count() == 0:
            raise KeyError, msgid

        messageID = results[0]

        sets = RosettaPOMessageSet.select('''
            potemplate = %d AND
            pofile IS NULL AND
            primemsgid = %d AND
            sequence > 0
            ''' % (self.id, msgid_obj.id))

        if sets.count() == 0:
            raise KeyError, msgid
        else:
            return sets[0]

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
            raise KeyError, \
                  "This template already has a POFile for %s variant %s" % \
                  (language.englishName, variant)
        language = RosettaLanguage.selectBy(code=language_code)
        if language.count() == 0:
            raise ValueError, "Unknown language"
        assert language.count() == 1
        language = language[0]
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
            }
        return RosettaPOFile(poTemplate=self,
                             language=language,
                             headerFuzzy=True,
                             title='%(languagename)s translation for %(productname)s' % data,
                             description="", # XXX: fill it
                             topComment=standardTemplateTopComment % data,
                             header=standardTemplateHeader % data,
                             lastTranslator=person,
                             currentCount=0,
                             updatesCount=0,
                             rosettaCount=0,
                             owner=person,
                             lastParsed="NOW",
                             pluralForms=language.pluralForms or 0,
                             variant=variant)

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

    def createMessageSetFromMessageID(self, messageID):
        return createMessageSetFromMessageID(self, messageID)

    def createMessageSetFromText(self, text):
        return createMessageSetFromText(self, text)


class RosettaPOFile(SQLBase):
    implements(IEditPOFile)

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
        StringCol(name='variant', dbName='variant'),
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

    def __getitem__(self, msgid):
        if type(msgid) is unicode:
            msgid = msgid.encode('utf-8')
        msgid_obj = RosettaPOMessageID.selectBy(msgid=msgid)
        if msgid_obj.count() == 0:
            raise KeyError, msgid
        msgid_obj = msgid_obj[0]
        sets = RosettaPOMessageSet.select('''
            pofile = %d AND
            primemsgid = %d
            ''' % (self.id, msgid_obj.id))
        if sets.count() == 0:
            raise KeyError, msgid
        else:
            return sets[0]

    def translated(self):
        res = RosettaPOMessageSet.select('''
            poSet.pofile = %d AND
            poSet.iscomplete=TRUE AND
            poSet.primemsgid = potset.primemsgid AND
            poSet.potemplate = potset.potemplate AND
            potSet.pofile IS NULL AND
            potSet.sequence <> 0''' % self.id,
            clauseTables = [
                'POMsgSet poSet',
                'POMsgSet potSet',
                ])
        return iter(res)

    # XXX: Implemented using the cache, we should add an option to get the
    # real count.
    # The number of translated are the ones from the .po file + the ones that
    # are only translated in Rosetta.
    def translatedCount(self):
        '''Returns the cached count of translated strings where translations
        exist in the files or in the database.'''
        return self.currentCount + self.rosettaCount

    def untranslated(self):
        '''XXX'''
        raise NotImplementedError

    # XXX: Implemented using the cache, we should add an option to get the
    # real count.
    # The number of untranslated are the ones from the .pot file - the ones
    # that we have already translated.
    def untranslatedCount(self):
        '''Same as untranslated(), but with COUNT.'''
        return len(self.poTemplate) - self.translatedCount()

    def messageSetsNotInTemplate(self):
        # this is rather complex because it's actually two queries that
        # have to be added together - if someone with more sql zen knows
        # how to do it in one query, feel free to refactor
        seqzero = RosettaPOMessageSet.select('''
            poSet.pofile = %d AND
            poSet.primemsgid = potset.primemsgid AND
            poSet.potemplate = potset.potemplate AND
            potSet.pofile IS NULL AND
            poSet.sequence <> 0 AND
            potSet.sequence = 0''' % self.id,
            clauseTables = [
                'POMsgSet poSet',
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
        self._connection.query('UPDATE POMsgSet SET sequence = 0'
                               ' WHERE pofile = %d'
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


class RosettaPOMessageSet(SQLBase):
    implements(IEditPOTemplateOrPOFileMessageSet)

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
            directlyProvides(self, IPOTemplateMessageSet)
        else:
            # this is a IPOFileMessageSet
            directlyProvides(self, IEditPOFileMessageSet)

    def messageIDs(self):
        return RosettaPOMessageID.select('''
            POMsgIDSighting.pomsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id AND
            POMsgIDSighting.inlastrevision = TRUE
            ''' % self.id, clauseTables=('POMsgIDSighting',))

    def getMessageIDSighting(self, plural_form, allowOld=False):
        """Return the message ID sighting that is current and has the
        plural form provided."""
        if allowOld:
            ret = RosettaPOMessageIDSighting.selectBy(poMessageSetID=self.id,
                                                      pluralForm=plural_form)
        else:
            ret = RosettaPOMessageIDSighting.selectBy(poMessageSetID=self.id,
                                                      pluralForm=plural_form,
                                                      inLastRevision=True)
        if ret.count() == 0:
            raise KeyError, plural_form
        else:
            return ret[0]

    def nplurals(self):
        if self.poFile is None:
            potset = self
        else:
            potset = RosettaPOMessageSet.select('''
                poTemplate = %d AND
                poFile IS NULL AND
                primemsgid = %d
                ''' % (self.poTemplate.id, self.primeMessageID_.id))
            if potset.count() == 0:
                # obsolete... try to get the count from self, although
                # that's not 100% reliable
                potset = self
            else:
                assert potset.count() == 1
                potset = potset[0]
        if potset.messageIDs().count() > 1:
            # has plurals
            if self.poFile is None:
                return 2
            return self.poFile.pluralForms
        else:
            return 1

    def translations(self):
        return RosettaPOTranslation.select('''
            POTranslationSighting.pomsgset = %d AND
            POTranslationSighting.potranslation = POTranslation.id
            ''' % self.id, clauseTables=('POTranslationSighting',))

    def translationsForLanguage(self, language):
        if self.poFile is not None:
            raise RuntimeError, """This method cannot be used with PO template
                message sets!"""

        # Find the number of plural forms.

        languages = getUtility(ILanguages)

        try:
            pofile = self.poTemplate.poFile(language)
            pluralforms = pofile.pluralForms
        except KeyError:
            pofile = None
            pluralforms = languages[language].pluralForms

        if pluralforms == None:
            raise RuntimeError, """Don't know the number of plural forms for
                this language! Bad call!"""

        if pofile is None:
            return [None] * pluralforms

        # XXX: We might want to look the number of plural forms up in the
        # language if the PO file exists but has .pluralForms == None.

        # Find the sibling message set.

        '''
        SELECT * FROM POMsgSet WHERE
            pofile = ${pofile} AND
            primemsgid = ${self.primemsgid} AND
            sequence > 0
        '''

        results = RosettaPOMessageSet.select('''pofile = %d AND primemsgid = %d AND
            sequence > 0''' % (pofile.id, self.primeMessageID_.id))

        assert 0 <= results.count() <= 1

        if results.count() == 0:
            return [None] * pluralforms

        translations = []
        translation_set = results[0]

        results = list(RosettaPOTranslationSighting.select(
            'pomsgset = %d AND active=True' % translation_set.id, orderBy='pluralForm'))

        for form in range(pluralforms):
            if results and results[0].pluralForm == form:
                translations.append(results.pop(0).poTranslation.translation)
            else:
                translations.append(None)

        return translations

    def getTranslationSighting(self, plural_form, allowOld=False):
        """Return the translation sighting that is committed and has the
        plural form provided."""
        if self.poFile == None:
            raise ValueError
        if allowOld:
            translations = RosettaPOTranslationSighting.selectBy(
                poMessageSetID=self.id,
                pluralForm=plural_form)
        else:
            translations = RosettaPOTranslationSighting.selectBy(
                poMessageSetID=self.id,
                inLastRevision=True,
                pluralForm=plural_form)
        if translations.count() == 0:
            raise IndexError, plural_form
        else:
            return translations[0]

    def translationSightings(self):
        if self.poFile == None:
            raise ValueError
        return RosettaPOTranslationSighting.selectBy(
            poMessageSetID=self.id)


    # IEditPOMessageSet

    def makeMessageIDSighting(self, text, plural_form, update=False):
        """Return a new message ID sighting that points back to us."""
        if type(text) is unicode:
            text = text.encode('utf-8')
        messageIDs = RosettaPOMessageID.selectBy(msgid=text)
        if messageIDs.count() == 0:
            messageID = RosettaPOMessageID(msgid=text)
        else:
            messageID = messageIDs[0]
        existing = RosettaPOMessageIDSighting.selectBy(
            poMessageSetID=self.id,
            poMessageID_ID=messageID.id,
            pluralForm=plural_form)
        if existing.count():
            assert existing.count() == 1
            if not update:
                raise KeyError, "There is already a message ID sighting for " \
                      "this message set, text, and plural form"
            existing = existing[0]
            existing.set(datelastSeen = "NOW", inLastRevision = True)
            return existing
        return RosettaPOMessageIDSighting(
            poMessageSet=self,
            poMessageID_=messageID,
            dateFirstSeen="NOW",
            dateLastSeen="NOW",
            inLastRevision=True,
            pluralForm=plural_form)

    def makeTranslationSighting(self, person, text, plural_form,
                              update=False, fromPOFile=False):
        """Return a new translation sighting that points back to us."""
        if type(text) is unicode:
            text = text.encode('utf-8')
        translations = RosettaPOTranslation.selectBy(translation=text)
        if translations.count() == 0:
            translation = RosettaPOTranslation(translation=text)
        else:
            translation = translations[0]
        existing = RosettaPOTranslationSighting.selectBy(
            poMessageSetID=self.id,
            poTranslationID=translation.id,
            pluralForm=plural_form,
            personID=person.id
            )
        if existing.count():
            assert existing.count() == 1
            if not update:
                raise KeyError, "There is already a translation sighting for " \
                      "this message set, text, and plural form"
            existing = existing[0]
            existing.set(dateLastActive="NOW",
                         active=True,
                         inLastRevision=existing.inLastRevision or fromPOFile)
            return existing
        if fromPOFile:
            origin = 1
        else:
            origin = 2
        return RosettaPOTranslationSighting(
            poMessageSet=self,
            poTranslation=translation,
            dateFirstSeen="NOW",
            dateLastActive="NOW",
            inLastRevision=fromPOFile,
            pluralForm=plural_form,
            active=True,
            person=person,
            origin=origin,
            license=1, # XXX: FIXME
            )


class RosettaPOMessageIDSighting(SQLBase):
    implements(IPOMessageIDSighting)

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
    implements(IPOMessageID)

    _table = 'POMsgID'

    _columns = [
        StringCol(name='msgid', dbName='msgid', notNull=True, unique=True)
    ]


class RosettaPOTranslationSighting(SQLBase):
    implements(IPOTranslationSighting)

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
    implements(IPOTranslation)

    _table = 'POTranslation'

    _columns = [
        StringCol(name='translation', dbName='translation', notNull=True, unique=True)
    ]

class RosettaLanguages(object):
    implements(ILanguages)

    def __getitem__(self, code):
        results = RosettaLanguage.selectBy(code=code)

        if results.count() == 0:
            raise KeyError, code
        else:
            return results[0]

    def keys(self):
        return [language.code for language in RosettaLanguage.select()]

class RosettaLanguage(SQLBase):
    implements(ILanguage)

    _table = 'Language'

    _columns = [
        StringCol(name='code', dbName='code', notNull=True, unique=True),
        StringCol(name='nativeName', dbName='nativename'),
        StringCol(name='englishName', dbName='englishname'),
        IntCol(name='pluralForms', dbName='pluralforms'),
        StringCol(name='pluralExpression', dbName='pluralexpression'),
    ]


class RosettaPerson(SQLBase):
    implements(IPerson)

    _table = 'Person'

    _columns = [
        StringCol(name='displayName', dbName='displayname'),
    ]

#    isMaintainer
#    isTranslator
#    isContributor

    # Invariant: isMaintainer implies isContributor

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

    # XXX: not fully implemented
    def languages(self):
        languages = getUtility(ILanguages)

        for code in ('ja', 'es'):
            yield languages[code]


class RosettaBranch(SQLBase):
    implements(IBranch)

    _table = 'Branch'

    _columns = [
        StringCol(name='title', dbName='title'),
        StringCol(name='description', dbName='description')
    ]


# XXX: This is cheating.
def personFromPrincipal(principal):
    ret = RosettaPerson.select()

    if ret.count() == 0:
        raise KeyError, principal
    else:
        return ret[0]

