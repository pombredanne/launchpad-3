from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.database.schema import Label

import canonical.launchpad.interfaces as interfaces

from sqlobject import ForeignKey, MultipleJoin, IntCol, StringCol

from zope.interface import implements

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


