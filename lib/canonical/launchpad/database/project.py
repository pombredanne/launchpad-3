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

    _columns = [
        ForeignKey(name='owner', foreignKey='Person', dbName='owner', \
            notNull=True),
        StringCol('name', notNull=True),
        StringCol('displayname', notNull=True),
        StringCol('title', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        # XXX: https://bugzilla.warthogs.hbd.com/bugzilla/show_bug.cgi?id=1968
        DateTimeCol('datecreated', notNull=True),
        StringCol('homepageurl', notNull=False, default=None),
        StringCol('wikiurl', notNull=False, default=None),
        StringCol('lastdoap', notNull=False, default=None)
    ]

    products = MultipleJoin('Product', joinColumn='project')

    _bugtrackers = RelatedJoin('BugTracker', joinColumn='project',
                                           otherColumn='bugtracker',
                                           intermediateTable='ProjectBugTracker')

    def bugtrackers(self):
        for bugtracker in self._bugtrackers:
            yield bugtracker

    def rosettaProducts(self):
        return iter(self.products)

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



#
# XXX Mark Shuttleworth 03/10/04 This classname is deprecated in favour of
#     ProjectSet below
#
class ProjectContainer(object):
    """A container for Project objects."""

    implements(IProjectContainer)
    table = Project

    def __getitem__(self, name):
        try:
            return self.table.select(self.table.q.name == name)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row

    def search(self, searchtext):
        q = """name LIKE '%%%%' || %s || '%%%%' """ % (
                quote(searchtext.lower())
                )
        q += """ OR lower(title) LIKE '%%%%' || %s || '%%%%'""" % (
                quote(searchtext.lower())
                )
        q += """ OR lower(shortdesc) LIKE '%%%%' || %s || '%%%%'""" % (
                quote(searchtext.lower())
                )
        q += """ OR lower(description) LIKE '%%%%' || %s || '%%%%'""" % (
                quote(searchtext.lower())
                )
        return Project.select(q)



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
        #
        # XXX Mark Shuttleworth 03/10/04 Should the "new" method to create
        #     a new project be on ProjectSet? or Project?
        #
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

    def search(self, query):
        query = quote('%%' + query + '%%')
        #query = quote(query)
        return Project.select(
            'title ILIKE %s OR description ILIKE %s' % (query, query))



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


