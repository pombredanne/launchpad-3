# arch-tag: da5d31ba-6994-4893-b252-83f4f66f0aba

from canonical.arch.sqlbase import SQLBase, quote
from canonical.rosetta.interfaces import *
from sqlobject import ForeignKey, MultipleJoin, IntCol, BoolCol, StringCol, \
    DateTimeCol
from zope.interface import implements
from canonical.rosetta import pofile
from types import NoneType
from datetime import datetime
from sets import Set

__metaclass__ = type

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


class RosettaProjects:
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
        name = name.encode('ascii')
        displayName = displayName.encode('ascii')
        title = title.encode('ascii')
        if type(url) != NoneType:
            url = url.encode('ascii')
        description = description.encode('ascii')

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


class RosettaProduct(SQLBase):
    implements(IProduct)

    _table = 'Product'

    _columns = [
        ForeignKey(name='project', foreignKey='RosettaProject', dbName='project',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True, unique=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
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

    def newPOTemplate(self, name, title):
        # XXX: we have to fill up a lot of other attributes
        if RosettaPOTemplate.selectBy(productID=self.id,
                                      name=name).count():
            raise KeyError, \
                  "This product already has a template named %s" % name
        return RosettaPOTemplate(name=name, title=title, product=self)


class RosettaPOTemplate(SQLBase):
    implements(IEditPOTemplate)

    _table = 'POTemplate'

    _columns = [
        ForeignKey(name='product', foreignKey='RosettaProduct', dbName='product',
            notNull=True),
        ForeignKey(name='owner', foreignKey='RosettaPerson', dbName='owner',
            notNull=True),
        StringCol(name='name', dbName='name', notNull=True, unique=True),
        StringCol(name='title', dbName='title', notNull=True, unique=True),
        StringCol(name='description', dbName='description', notNull=True),
        StringCol(name='path', dbName='path', notNull=True),
        BoolCol(name='isCurrent', dbName='iscurrent', notNull=True),
        DateTimeCol(name='dateCreated', dbName='datecreated'),
        StringCol(name='copyright', dbName='copyright'),
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
        return self.currentMessageSets().count()

    def __getitem__(self, msgid):
        if type(msgid) is unicode:
            msgid = msgid.encode('utf-8')
        msgid_obj = RosettaPOMessageID.selectBy(msgid=msgid)
        if msgid_obj.count() == 0:
            raise KeyError, msgid
        msgid_obj = msgid_obj[0]
        sets = RosettaPOMessageSet.select('''
            potemplate = %d AND
            pofile IS NULL AND
            primemsgid = %d
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

    def makeMessageSet(self, text, pofile=None, update=False):
        if type(text) is unicode:
            text = text.encode('utf-8')
        messageIDs = RosettaPOMessageID.selectBy(msgid=text)
        if messageIDs.count() == 0:
            messageID = RosettaPOMessageID(msgid=text)
        else:
            assert messageIDs.count() == 1
            messageID = messageIDs[0]
            existing = RosettaPOMessageSet.selectBy(
                poTemplateID=self.id,
                poFileID=(pofile and pofile.id),
                primeMessageID_ID=messageID.id)
            if existing.count():
                assert existing.count() == 1
                if not update:
                    raise KeyError, "There is already a message set for " \
                          "this template, file and primary msgid"
                existing = existing[0]
                return existing
        msgSet = RosettaPOMessageSet(poTemplate=self,
                                   poFile=pofile,
                                   primeMessageID_=messageID,
                                   sequence=0,
                                   isComplete=False,
                                   obsolete=False,
                                   fuzzy=False,
                                   commentText='',
                                   fileReferences='',
                                   sourceComment='',
                                   flagsComment='')
        sighting = RosettaPOMessageIDSighting(poMessageSet=msgSet,
                                              poMessageID_=messageID,
                                              dateFirstSeen="NOW",
                                              dateLastSeen="NOW",
                                              inLatestRevision=False,
                                              pluralForm=0)
        return msgSet

    def newPOFile(self, language, variant=None):
        # assume we are getting a IRosettaLanguage object
        if RosettaPOFile.selectBy(poTemplate=self,
                                  language=language,
                                  variant=variant).count():
            raise KeyError, \
                  "This template already has a POFile for %s variant %s" % \
                  (language.englishName, variant)
        now = datetime.now()
        data = {
            'year': now.year,
            'languagename': language.englishName,
            'languagecode': language.code,
            'productname': self.product.title,
            'date': now.isoformat(' '),
            'templatedate': self.datecreated.gmtime().Format('%Y-%m-%d %H:%M+000'),
            'copyright': self.copyright,
            }
        return RosettaPOFile(poTemplate=self,
                             language=language,
                             fuzzyHeader=True,
                             title='%(languagename)s translation for %(productname)s' % data,
                             #description="",
                             topComment=standardTemplateTopComment % data,
                             header=standardTemplateHeader % data,
                             #lastTranslator=XXX: FIXME,
                             translatedCountCached=0,
                             #updatesCount=0,
                             rosettaOnlyCountCached=0,
                             #owner=XXX: FIXME,
                             pluralForms=2, #FIXME
                             variant=variant)


class RosettaPOFile(SQLBase):
    implements(IEditPOFile)

    _table = 'POFile'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='RosettaPOTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='language', foreignKey='RosettaLanguage', dbName='language',
            notNull=True),
        StringCol(name='title', dbName='title', notNull=True, unique=True),
        StringCol(name='description', dbName='description', notNull=True),
        StringCol(name='topComment', dbName='topcomment', notNull=True),
        StringCol(name='header', dbName='header', notNull=True),
        BoolCol(name='headerFuzzy', dbName='fuzzyheader', notNull=True),
        IntCol(name='translatedCountCached', dbName='currentcount',
            notNull=True),
        IntCol(name='rosettaOnlyCountCached', dbName='rosettacount',
            notNull=True),
        IntCol(name='pluralForms', dbName='pluralforms')
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
        return self.translatedCountCached + self.rosettaOnlyCountCached

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

    # IEditPOFile
    def expireAllMessages(self):
        self._connection.query('UPDATE POMsgSet SET sequence = 0'
                               ' WHERE pofile = %d'
                               % self.id)


class RosettaPOMessageSet(SQLBase):
    implements(IEditPOMessageSet)

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

    def messageIDs(self):
        return RosettaPOMessageID.select('''
            POMsgIDSighting.pomsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id
            ''' % self.id, clauseTables=('POMsgIDSighting',))

    def getMessageIDSighting(self, plural_form):
        """Return the message ID sighting that is current and has the
        plural form provided."""
        ret = RosettaPOMessageIDSighting.selectBy(poMessageSetID=self.id,
                                                  pluralForm=plural_form,
                                                  inpofile=True)
        if ret.count() == 0:
            raise KeyError, plural_form
        else:
            return ret[0]

    def newTranslation(self, sighting_or_msgid):
        raise NotImplementedError


    def translations(self):
        return RosettaPOTranslation.select('''
            POTranslationSighting.pomsgset = %d AND
            POTranslationSighting.potranslation = POTranslation.id
            ''' % self.id, clauseTables=('POTranslationSighting',))

    def getTranslationsForThatPOMessageSetOverThere(self):
        '''
        SELECT DISTINCT ON (sighting.pluralform) sighting.* FROM
            POMsgSet potset,
            POMsgSet poset,
            POFile pofile,
            POTranslation translation,
            POTranslationSighting sighting
            WHERE
            potset.id = 5 AND
            potset.pofile IS NULL AND
            potset.potemplate = pofile.potemplate AND
            pofile.id = poset.pofile AND
            potset.primemsgid = poset.primemsgid AND
            poset.id = sighting.pomsgset AND
            sighting.potranslation = translation.id
            ORDER BY sighting.pluralform, sighting.lasttouched
        '''

    def getTranslationSighting(self, plural_form):
        """Return the translation sighting that is committed and has the
        plural form provided."""
        if self.poFile == None:
            raise ValueError
        translations = RosettaPOTranslationSighting.selectBy(
            poMessageSetID=self.id,
            inLatestRevision=True,
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
            existing.set(datelastSeen = "NOW", inLatestRevision = True)
            return existing
        return RosettaPOMessageIDSighting(
            poMessageSet=self,
            poMessageID_=messageID,
            dateFirstSeen="NOW",
            dateLastSeen="NOW",
            inLatestRevision=True,
            pluralForm=plural_form)

    def makeTranslationSighting(self, text, plural_form, update=False, fromPOFile=False):
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
            #person='XXX FIXME'
            )
        if existing.count():
            assert existing.count() == 1
            if not update:
                raise KeyError, "There is already a translation sighting for " \
                      "this message set, text, and plural form"
            existing = existing[0]
            existing.set(dateLastActive="NOW",
                         active=True,
                         inLatestRevision=existing.inLatestRevision or fromPOFile)
            return existing
        return RosettaPOTranslationSighting(
            poMessageSet=self,
            poTranslation=translation,
            dateFirstSeen="NOW",
            dateLastActive="NOW",
            inLatestRevision=fromPOFile,
            pluralForm=plural_form,
            active=True,
            person=0, #'XXX FIXME'
            )


class RosettaPOMessageIDSighting(SQLBase):
    implements(IPOMessageIDSighting)

    _table = 'POMsgIDSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='RosettaPOMessageSet', dbName='pomsgset', notNull=True),
        ForeignKey(name='poMessageID_', foreignKey='RosettaPOMessageID', dbName='pomsgid', notNull=True),
        DateTimeCol(name='dateFirstSeen', dbName='datefirstseen', notNull=True),
        DateTimeCol(name='dateLastSeen', dbName='datelastseen', notNull=True),
        BoolCol(name='inLatestRevision', dbName='inlatestrevision', notNull=True),
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
        # license
        DateTimeCol(name='dateFirstSeen', dbName='datefirstseen', notNull=True),
        DateTimeCol(name='dateLastActive', dbName='datelastactive', notNull=True),
        BoolCol(name='inLatestRevision', dbName='inlatestrevision', notNull=True),
        IntCol(name='pluralForm', dbName='pluralform', notNull=True),
        # See canonical.lp.dbschema.RosettaTranslationOrigin.
        IntCol(name='origin', dbName='origin', notNull=True),
        BoolCol(name='active', dbName='active', notNull=True),
    ]


class RosettaPOTranslation(SQLBase):
    implements(IPOTranslation)

    _table = 'POTranslation'

    _columns = [
        StringCol(name='translation', dbName='translation', notNull=True, unique=True)
    ]

class RosettaLanguages:
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
        for code in ('cy', 'es'):
            yield RosettaLanguage.selectBy(code=code)[0]


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

