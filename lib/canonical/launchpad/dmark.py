
# Zope interfaces
from zope.interface import implements
from zope.component import ComponentLookupError
from zope.app.security.interfaces import IUnauthenticatedPrincipal

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
import canonical.launchpad.interfaces as interfaces
from canonical.launchpad.interfaces import *
from canonical.launchpad.database import *


class SourceSource(SQLBase): 
    #, importd.Job.Job):
    #from canonical.soyuz.sql import SourcePackage, Branch
    """SourceSource table!"""

    _table = 'SourceSource'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        # Mark Shuttleworth 03/10/04 Robert Collins why is this default=1?
        ForeignKey(name='product', foreignKey='Product', dbName='product',
                   default=1),
        StringCol('cvsroot', dbName='cvsroot', default=None),
        StringCol('cvsmodule', dbName='cvsmodule', default=None),
        ForeignKey(name='cvstarfile', foreignKey='LibraryFileAlias',
                   dbName='cvstarfile', default=None),
        StringCol('cvstarfileurl', dbName='cvstarfileurl', default=None),
        StringCol('cvsbranch', dbName='cvsbranch', default=None),
        StringCol('svnrepository', dbName='svnrepository', default=None),
        StringCol('releaseroot', dbName='releaseroot', default=None),
        StringCol('releaseverstyle', dbName='releaseverstyle', default=None),
        StringCol('releasefileglob', dbName='releasefileglob', default=None),
        ForeignKey(name='releaseparentbranch', foreignKey='Branch',
                   dbName='releaseparentbranch', default=None),
        ForeignKey(name='sourcepackage', foreignKey='SourcePackage',
                   dbName='sourcepackage', default=None),
        ForeignKey(name='branch', foreignKey='Branch',
                   dbName='branch', default=None),
        DateTimeCol('lastsynced', dbName='lastsynced', default=None),
        DateTimeCol('frequency', dbName='syncinterval', default=None),
        # WARNING: syncinterval column type is "interval", not "integer"
        # WARNING: make sure the data is what buildbot expects
        #IntCol('rcstype', dbName='rcstype', default=RCSTypeEnum.cvs,
        #       notNull=True),
        # FIXME: use 'RCSTypeEnum.cvs' rather than '1'
        IntCol('rcstype', dbName='rcstype', default=1,
               notNull=True),
        StringCol('hosted', dbName='hosted', default=None),
        StringCol('upstreamname', dbName='upstreamname', default=None),
        DateTimeCol('processingapproved', dbName='processingapproved',
                    notNull=False, default=None),
        DateTimeCol('syncingapproved', dbName='syncingapproved', notNull=False,
                    default=None),
        # For when Rob approves it
        StringCol('newarchive', dbName='newarchive'),
        StringCol('newbranchcategory', dbName='newbranchcategory'),
        StringCol('newbranchbranch', dbName='newbranchbranch'),
        StringCol('newbranchversion', dbName='newbranchversion'),
        # Temporary keybuk stuff
        StringCol('package_distro', dbName='packagedistro', default=None),
        StringCol('package_files_collapsed', dbName='packagefiles_collapsed',
                default=None),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
                   notNull=True),
        StringCol('currentgpgkey', dbName='currentgpgkey', default=None),
    ]

class Person(SQLBase):
    """A Person."""

    implements(IPerson)

    _columns = [
        StringCol('name', default=None),
        StringCol('displayname', default=None),
        StringCol('givenname', default=None),
        StringCol('familyname', default=None),
        StringCol('password', default=None),
        ForeignKey(name='teamowner', foreignKey='Person', dbName='teamowner'),
        StringCol('teamdescription', default=None),
        IntCol('karma'),
        DateTimeCol('karmatimestamp')
    ]

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
        return POTemplate.select('''
            id IN (SELECT potemplate FROM pomsgset WHERE
                id IN (SELECT pomsgset FROM POTranslationSighting WHERE
                    origin = 2
                ORDER BY datefirstseen DESC))
            ''')

    _labelsJoin = RelatedJoin('Label', joinColumn='person',
        otherColumn='label', intermediateTable='PersonLabel')

    def languages(self):
        languages = getUtility(interfaces.ILanguages)
        try:
            schema = Schema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")

        for label in self._labelsJoin:
            if label.schema == schema:
                yield languages[label.name]

    def addLanguage(self, language):
        try:
            schema = Schema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        label = Label.selectBy(schemaID=schema.id, name=language.code)
        if label.count() < 1:
            # The label for this language does not exists yet into the
            # database, we should create it.
            label = Label(
                        schemaID=schema.id,
                        name=language.code,
                        title='Translates into ' + language.englishName,
                        description='A person with this label says that ' + \
                                    'knows how to translate into ' + \
                                    language.englishName)
        else:
            label = label[0]
        # This method comes from the RelatedJoin
        self.addLabel(label)

    def removeLanguage(self, language):
        try:
            schema = Schema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        label = Label.selectBy(schemaID=schema.id, name=language.code)[0]
        # This method comes from the RelatedJoin
        self.removeLabel(label)



def personFromPrincipal(principal):
    """Adapt canonical.lp.placelessauth.interfaces.ILaunchpadPrincipal 
       to IPerson
    """
    if IUnauthenticatedPrincipal.providedBy(principal):
        # When Zope3 interfaces allow returning None for "cannot adapt"
        # we can return None here.
        ##return None
        raise ComponentLookupError
    return Person.get(principal.id)


class EmailAddress(SQLBase):
    implements(IEmailAddress)

    _table = 'EmailAddress'
    _columns = [
        StringCol('email', notNull=True, unique=True),
        IntCol('status', notNull=True),
        ForeignKey(
            name='person', dbName='person', foreignKey='Person',
            )
        ]


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
    _productsJoin = MultipleJoin('Product', joinColumn='project')

    def rosettaProducts(self):
        return iter(self._productsJoin)

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


class Product(SQLBase):
    """A Product."""

    implements(IProduct)

    _table = 'Product'

    _columns = [
        ForeignKey(
                name='project', foreignKey="Project", dbName="project",
                notNull=True
                ),
        ForeignKey(
                name='owner', foreignKey="Product", dbName="owner",
                notNull=True
                ),
        StringCol('name', notNull=True),
        StringCol('displayname', notNull=True),
        StringCol('title', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        DateTimeCol('datecreated', notNull=True),
        StringCol('homepageurl', notNull=False, default=None),
        StringCol('screenshotsurl', notNull=False, default=None),
        StringCol('wikiurl', notNull=False, default=None),
        StringCol('programminglang', notNull=False, default=None),
        StringCol('downloadurl', notNull=False, default=None),
        StringCol('lastdoap', notNull=False, default=None),
        ]

    _poTemplatesJoin = MultipleJoin('POTemplate', joinColumn='product')

    bugs = MultipleJoin('ProductBugAssignment', joinColumn='product')

    sourcesources = MultipleJoin('SourceSource', joinColumn='product')

    def poTemplates(self):
        return iter(self._poTemplatesJoin)

    def poTemplate(self, name):
        '''SELECT POTemplate.* FROM POTemplate WHERE
              POTemplate.product = id AND
              POTemplate.name = name;'''
        results = POTemplate.select('''
            POTemplate.product = %d AND
            POTemplate.name = %s''' %
            (self.id, quote(name)))

        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]

    def newPOTemplate(self, person, name, title):
        # XXX: we have to fill up a lot of other attributes
        if POTemplate.selectBy(
                productID=self.id, name=name).count():
            raise KeyError(
                  "This product already has a template named %s" % name)
        return POTemplate(name=name, title=title, product=self)

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

