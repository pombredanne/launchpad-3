"""Launchpad Project-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements

# SQL object
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# Launchpad interfaces
from canonical.launchpad.interfaces import *

# Import needed database objects
from canonical.launchpad.database.person import Person
from canonical.launchpad.database.product import Product


class Project(SQLBase):
    """A Project"""

    implements(IProject)

    _table = "Project"

    # db field names
    owner= ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    displayname = StringCol(dbName='displayname', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    shortdesc = StringCol(dbName='shortdesc', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    # XXX: https://bugzilla.warthogs.hbd.com/bugzilla/show_bug.cgi?id=1968
    datecreated = DateTimeCol(dbName='datecreated', notNull=True)
    homepageurl = StringCol(dbName='homepageurl', notNull=False, default=None)
    wikiurl = StringCol(dbName='wikiurl', notNull=False, default=None)
    lastdoap = StringCol(dbName='lastdoap', notNull=False, default=None)
    active = BoolCol(dbName='active', notNull=True, default=True)
    reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)
    
    # convenient joins
    _products = MultipleJoin('Product', joinColumn='project')

    _bugtrackers = RelatedJoin('BugTracker', joinColumn='project',
                                           otherColumn='bugtracker',
                                           intermediateTable='ProjectBugTracker')

    def bugtrackers(self):
        for bugtracker in self._bugtrackers:
            yield bugtracker

    def products(self):
        for product in self._products:
            yield product

    def getProduct(self, name):
        try:
            return Product.selectBy(projectID=self.id, name=name)[0]
        except IndexError:
            return None

    def poTemplate(self, name):
        # XXX: What does this have to do with Project?  This function never
        # uses self.  I suspect this belongs somewhere else.
        results = RosettaPOTemplate.selectBy(name=name)
        count = results.count()

        if count == 0:
            raise KeyError, name
        elif count == 1:
            return results[0]
        else:
            raise AssertionError("Too many results.")

class ProjectSet:
    implements(IProjectSet)

    def __iter__(self):
        return iter(Project.select())

    def __getitem__(self, name):
        ret = Project.selectBy(name=name)

        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

    def new(self, name, displayname, title, homepageurl, shortdesc, 
            description, owner):
        name = name.encode('ascii')
        displayname = displayname.encode('ascii')
        title = title.encode('ascii')
        if type(url) != NoneType:
            url = url.encode('ascii')
        description = description.encode('ascii')

        if Project.selectBy(name=name).count():
            raise KeyError, "There is already a project with that name"

        return Project(name = name,
                       displayname = displayname,
                       title = title,
                       shortdesc = shortdesc,
                       description = description,
                       homepageurl = url,
                       owner = owner,
                       datecreated = 'now')

    def forReview(self):
        query = """Product.project=Project.id AND
                 ( Product.reviewed IS FALSE OR
                   Project.reviewed IS FALSE )"""
        clauseTables = ['Project', 'Product']
        results = []
        for project in Project.select(query, clauseTables=clauseTables):
            if project not in results:
                results.append(project)
        return results

    def forSyncReview(self):
        query = """Product.project=Project.id AND
                 ( Product.reviewed IS FALSE OR
                   Project.reviewed IS FALSE )"""
        clauseTables = ['Project', 'Product']
        results = []
        for project in Project.select(query, clauseTables=clauseTables):
            if project not in results:
                results.append(project)
        return results


    def search(self, query, search_products = False):
        query = quote('%' + query + '%')

        condition = ('title ILIKE %s OR description ILIKE %s' %
            (query, query))

        if search_products:
            condition += (' OR id IN (SELECT project FROM Product WHERE '
                'title ILIKE %s OR description ILIKE %s)' % (query, query))

        return Project.select(condition)


class ProjectBugTracker(SQLBase):
    """Implements the IProjectBugTracker interface, for access to the
    ProjectBugTracker table."""
    implements(IProjectBugTracker)

    _table = 'ProjectBugTracker'

    _columns = [
        ForeignKey(
                name='project', foreignKey="Project",
                dbName="project", notNull=True
                ),
        ForeignKey(
                name='bugtracker', foreignKey="BugTracker",
                dbName="bugtracker",
                notNull=True
                ),
                ]


