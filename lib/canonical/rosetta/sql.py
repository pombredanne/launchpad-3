# arch-tag: da5d31ba-6994-4893-b252-83f4f66f0aba

from canonical.arch.sqlbase import SQLBase, quote
from canonical.rosetta.interfaces import IProjects, IProject, IProduct, \
    IPOTemplate, IPOFile, IPOMessageSet, IPOMessageIDSighting, IPOMessageID, \
    IPOTranslationSighting, IPOTranslation, ILanguage, ILanguages, IPerson
from sqlobject import ForeignKey, MultipleJoin, IntCol, BoolCol, StringCol, \
    DateTimeCol
from zope.interface import implements
from canonical.rosetta import pofile

__metaclass__ = type

class RosettaProjects:
    implements(IProjects)

    def __iter__(self):
        return iter(RosettaProject.select())

    def __getitem__(self, name):
        return RosettaProject.selectBy(name=name)[0]

    def new(self, name, title, url, description, owner):
        return RosettaProject(name=name, title=title, url=url,
            description=description, owner=owner, datecreated='now')


class RosettaProject(SQLBase):
    implements(IProject)

    _table = 'Project'

    _columns = [
        ForeignKey(name='owner', foreignKey='RosettaPerson', dbName='owner',
            notNull=True),
        StringCol('name', dbName='name', notNull=True, unique=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        StringCol('url', dbName='homepageurl')
    ]

    products = MultipleJoin('RosettaProduct', joinColumn='project')

    def poTemplates(self):
        for p in self.products:
            for t in p.poTemplates:
                yield t

    def poTemplate(self, name):
        '''SELECT POTemplate.* FROM POTemplate, Product WHERE
            POTemplate.product = Product.id AND
            Product.project = id AND
            POTemplate.name = name;'''
        #raise NotImplementedError
        #import pdb; pdb.set_trace()
        results = RosettaPOTemplate.select('''
            POTemplate.product = Product.id AND
            Product.project = %d AND
            POTemplate.name = %s''' %
            (self.id, quote(name)),
            clauseTables=('Product',))

        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]


class RosettaProduct(SQLBase):
    implements(IProduct)

    _table = 'Product'

    _columns = [
        ForeignKey(name='project', foreignKey='RosettaProject', dbName='project',
            notNull=True),
        StringCol('name', dbName='name', notNull=True, unique=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
    ]

    poTemplates = MultipleJoin('RosettaPOTemplate', joinColumn='product')

    def newPOTemplate(self, name, title):
        return RosettaPOTemplate(name=name, title=title, product=self)


class RosettaPOTemplate(SQLBase):
    implements(IPOTemplate)

    _table = 'POTemplate'

    _columns = [
        ForeignKey(name='product', foreignKey='RosettaProduct', dbName='product',
            notNull=True),
        StringCol('name', dbName='name', notNull=True, unique=True),
        StringCol('title', dbName='title', notNull=True, unique=True),
    ]

    poFiles = MultipleJoin('RosettaPOFile', joinColumn='potemplate')

    def languages(self):
        '''SELECT Language.* FROM POFile, Language WHERE
            POFile.language = Language.id AND
            POFile.potemplate = self.id;'''
        return RosettaLanguage.select('''
            POFile.language = Language.id AND POFile.potemplate = %d
            ''' % self.id, clauseTables=('POFile', 'Language'))

    def poFile(self, code):
        '''SELECT POFile.* FROM POTemplate, POFile, Language WHERE
            POFile.template = POTemplate.id AND
            POFile.language = Language.id AND
            Language.code = code;'''
        ret = RosettaPOFile.select("""
            POFile.potemplate = %d AND
            POFile.language = Language.id AND
            Language.code = %s
            """ % (self.id, quote(code)),
            clauseTables=('Language',))

        if ret.count() == 0:
            raise KeyError, code
        else:
            return ret[0]

    def __iter__(self):
        '''
        POMsgSet.potemplate = %d AND
        POMsgSet.pofile IS NULL
        '''
        '''
        SELECT POMsgSet.* FROM POMsgSet WHERE
        POMsgSet.potfile = self.id AND
        POMsgSet.iscurrent = true;
        '''
        #return iter(RosettaPOMessageSet.selectBy(poTemplateID = self.id, poFileID = None))
        return iter(RosettaPOMessageSet.select(
            '''
            POMsgSet.potemplate = %d AND
            POMsgSet.pofile IS NULL
            '''
            % self.id))

    def __len__(self):
        '''Same query as __iter__, but with COUNT.'''
        #raise NotImplementedError
        return RosettaPOMessageSet.select(
            '''
            POMsgSet.potemplate = %d AND
            POMsgSet.pofile IS NULL
            '''
            % self.id).count()


class RosettaPOFile(SQLBase):
    implements(IPOFile)

    _table = 'POFile'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='RosettaPOTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='language', foreignKey='RosettaLanguage', dbName='language',
            notNull=True)
        # XXX: missing fields
    ]

    # XXX: ???
    __iter__ = MultipleJoin('RosettaPOMessageSet', joinColumn='pofile')

    # XXX: not implemented
    def __len__(self):
        '''Count of __iter__.'''
        return 26

    def __getitem__(self, messageSet):
        '''
        SELECT POMessageSet.* FROM
            POMsgSet poSet,
            POMsgSet potSet,
            POTemplate self,
            POFile pofile,
            POMsgID pomsgid
        WHERE
            pofile.potemplate = {self.id} AND
            poSet.pofile = pofile.id AND
            poSet.pomsgid = pomsgid.id AND
            potSet.potemplate = {self.poTemplate.id} AND
            potSet.pomsgid = pomsgid.id;
        '''
        return RosettaPOMessageSet.select('''
            pofile.potemplate = %d AND
            poSet.id = %d AND
            poSet.pomsgid = pomsgid.id AND
            potSet.potemplate = %d AND
            potSet.pomsgid = pomsgid.id''' % \
            (self.id, messageSet.id, self.poTemplate.id),
            clauseTables = [
                'POMsgSet poSet',
                'POMsgSet potSet',
                'POTemplate template',
                'POFile pofile',
                'POMsgID pomsgid',
                ])

    def translated(self):
        '''
        SELECT POMsgSet.* FROM
            POMsgSet,
            POTranslationSighting
        WHERE
            POMsgSet.pofile = self.id AND
            POTranslationSighting.pomsgset = POMsgSet.id;
        '''
        raise NotImplementedError


    # XXX: not implemented
    def translated_count(self):
        '''Same as translated(), but with COUNT.'''
        return 14

    def untranslated(self):
        '''XXX'''
        raise NotImplementedError

    # XXX: not implemented
    def untranslated_count(self):
        '''Same as untranslated(), but with COUNT.'''
        return 9


class RosettaPOMessageSet(SQLBase):
    implements(IPOMessageSet)

    _table = 'POMsgSet'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='RosettaPOTemplate', dbName='potemplate', notNull=False),
        ForeignKey(name='poFile', foreignKey='RosettaPOFile', dbName='pofile', notNull=False),
        IntCol(name='sequence', dbName='sequence', notNull=False),
        BoolCol(name='isComplete', dbName='iscomplete', notNull=True),
        BoolCol(name='fuzzy', dbName='fuzzy', notNull=True),
        BoolCol(name='obsolete', dbName='obsolete', notNull=True),
        StringCol(name='commentText', dbName='commenttext', notNull=False),
        StringCol(name='fileReferences', dbName='filereferences', notNull=False),
        StringCol(name='sourceComment', dbName='sourcecomment', notNull=False),
    ]

    def messageIDs(self):
        return RosettaPOMessageID.select('''
            POMsgIDSighting.pomsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id
            ''' % self.id, clauseTables=('POMsgIDSighting',))

    def translations(self):
        return RosettaPOTranslation.select('''
            POTranslationSighting.pomessageset = %d AND
            POMessageIDSighting.potranslation = POTranslation.id
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

class RosettaPOMessageIDSighting(SQLBase):
    implements(IPOMessageIDSighting)

    _table = 'POMsgIDSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='RosettaPOMsgSet', dbName='pomsgset', notNull=True),
        ForeignKey(name='poMessageID', foreignKey='RosettaPOMsgID', dbName='pomsgid', notNull=True),
        DateTimeCol(name='firstSeen', dbName='firstseen', notNull=True),
        DateTimeCol(name='lastSeen', dbName='lastseen', notNull=True),
        BoolCol(name='inPOFile', dbName='inpofile', notNull=True),
        IntCol(name='pluralForm', dbName='pluralform', notNull=True),
    ]


class RosettaPOMessageID(SQLBase):
    implements(IPOMessageID)

    _table = 'POMsgID'

    _columns = [
        StringCol(name='text', dbName='msgid', notNull=True, unique=True)
    ]

class RosettaPOTranslationSighting(SQLBase):
    implements(IPOTranslationSighting)

    _table = 'POTranslationSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='RosettaPOMessageSet',
            dbName='pomsgset', notNull=True),
        ForeignKey(name='poTranslation', foreignKey='RosettPOTranslation',
            dbName='potranslation', notNull=True),
        ForeignKey(name='person', foreignKey='RosettaPerson',
            dbName='person', notNull=True),
        # license
        DateTimeCol(name='firstSeen', dbName='firstseen', notNull=True),
        DateTimeCol(name='lastTouched', dbName='lasttouched', notNull=True),
        BoolCol(name='inPOFile', dbName='inpofile', notNull=True),
        IntCol(name='pluralForm', dbName='pluralform', notNull=True),
        BoolCol(name='deprecated', dbName='deprecated', notNull=True),
    ]


class RosettaPOTranslation(SQLBase):
    implements(IPOTranslation)

    _table = 'POTranslation'

    _columns = [
        StringCol(name='text', dbName='translation', notNull=True, unique=True)
    ]

class RosettaLanguages:
    implements(ILanguages)

    def __getitem__(self, code):
        return Language.selectBy(code=code)

    def keys(self):
        for code in Language.select()[0]:
            yield code

class RosettaLanguage(SQLBase):
    implements(ILanguage)

    _table = 'Language'

    _columns = [
        StringCol(name='code', dbName='code', notNull=True, unique=True),
        StringCol(name='nativeName', dbName='nativename'),
        StringCol(name='englishName', dbName='englishname')
    ]

class RosettaPerson(SQLBase):
    implements(IPerson)

    _table = 'Person'

#    _columns = [
#        StringCol(name='', dbName='', NotNull=, unique=),
#    ]

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

    # XXX: not implemented
    def languages():
        '''languages = getUtility(ILanguages)
        for code in ('cy', 'no', 'es'):
            yield languages[code]
        '''

# POFile import
class POMessage(pofile.POMessage):
    def finish(self):
        assert (self.pofile is None) or (self.potemplate is None)
        assert (self.pofile is not None) or (self.potemplate is not None)
        pofile.POMessage.finish(self)

class POHeader(pofile.POHeader):
    def finish(self):
        assert (self.pofile is None) or (self.potemplate is None)
        assert (self.pofile is not None) or (self.potemplate is not None)
        pofile.POHeader.finish(self)

class FactoryForPOFile(object):
    def __init__(self, pofile, real_class):
        self.pofile = pofile
        self.real_class = real_class

    def __call__(self, **kw):
        instance = self.real_class(**kw)
        instance.pofile = self.pofile
        instance.potemplate = None
        return instance

class FactoryForPOTemplate(object):
    def __init__(self, potemplate, real_class):
        self.potemplate = potemplate
        self.real_class = real_class

    def __call__(self, **kw):
        instance = self.real_class(**kw)
        instance.pofile = None
        instance.potemplate = self.potemplate
        return instance
