# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Category', 'TranslationEfforts', 'TranslationEffort',
           'TranslationEffortPOTemplate']

from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.database.schema import Label

from canonical.launchpad.interfaces import \
    ICategory, ITranslationEffort, ITranslationEfforts, \
    ITranslationEffortPOTemplate

from sqlobject import ForeignKey, MultipleJoin, StringCol

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import TranslationPriority

from zope.interface import implements


class Category(Label):
    implements(ICategory)

    _effortPOTemplatesJoin = MultipleJoin('TranslationEffortPOTemplate',
        joinColumn='category')

    def poTemplates(self):
        # XXX: We assume that template will have always a row because the
        # database's referencial integrity
        for effortPOTemplate in self._effortPOTemplatesJoin:
            template = POTemplate.selectOneBy(id=effortPOTemplate.poTemplate)
            yield template

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


class TranslationEfforts:
    implements(ITranslationEfforts)

    def __iter__(self):
        return iter(TranslationEffort.select())

    def __getitem__(self, name):
        ret = TranslationEffort.selectOneBy(name=name)
        if ret is None:
            raise KeyError, name
        return ret

    def new(self, name, title, shortDescription, description, owner, project):
        if TranslationEffort.selectBy(name=name).count():
            raise KeyError(
                "There is already a translation effort with that name")
        return TranslationEffort(name=name,
                                 title=title,
                                 shortDescription=shortDescription,
                                 description=description,
                                 owner=owner, project=project)

    def search(self, query):
        query = '%% || %s || %%' % quote_like(query)
        # XXX: stub needs to make this use full text indexes.
        return TranslationEffort.select(
            'title ILIKE %s  OR description ILIKE %s' % (query, query))


class TranslationEffort(SQLBase):
    implements(ITranslationEffort)

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
        StringCol(name='shortDescription', dbName='summary', notNull=True),
        StringCol(name='description', dbName='description', notNull=True)
        ]

    def categories(self):
        """SELECT * FROM Label WHERE schema=self.categories"""
        return iter(Category.selectBy(schema=self.categories))

    def category(self, name):
        ret = Category.selectOneBy(name=name, schema=self.categories)
        if ret is None:
            raise KeyError(name)
        return ret

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
    implements(ITranslationEffortPOTemplate)

    _table = 'TranslationEffortPOTemplate'

    _columns = [
        ForeignKey(name='translationEffort',
            foreignKey='TranslationEffort', dbName='translationeffort',
            notNull=True),
        ForeignKey(name='poTemplate', foreignKey='POTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='category', foreignKey='Category',
            dbName='category', notNull=False),
        EnumCol(name='priority', dbName='priority', notNull=True,
            schema=TranslationPriority),
        ]

