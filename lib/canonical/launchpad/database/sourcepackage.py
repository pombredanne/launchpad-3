# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Python Imports
from sets import Set

# Zope Imports
from zope.interface import implements

# SQL Imports
from sqlobject import MultipleJoin
from sqlobject import StringCol, ForeignKey, MultipleJoin, DateTimeCol, \
     RelatedJoin
from canonical.database.sqlbase import SQLBase, quote

# Launchpad Imports
from canonical.lp.dbschema import EnumCol, \
        SourcePackageFormat, BugTaskStatus, BugSeverity, \
        PackagePublishingStatus

from canonical.launchpad.interfaces import ISourcePackage, ISourcePackageSet
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.bugtask import BugTask
from canonical.launchpad.database.vsourcepackagereleasepublishing import \
    VSourcePackageReleasePublishing
from canonical.launchpad.database.sourcepackageindistro import \
    SourcePackageInDistro
from canonical.launchpad.database.sourcepackagerelease import \
    SourcePackageRelease
from canonical.launchpad.database.sourcepackagename import \
    SourcePackageName
from canonical.launchpad.database.pofile import POTemplate

class SourcePackage(object):
    """A source package, e.g. apache2, in a distribution or distrorelease.
    This object implements the MagicSourcePackage specification. It is not a
    true database object, but rather attempts to represent the concept of a
    source package in a distribution, with links to the relevant dataase
    objects.
    
    Note that the Magic SourcePackage can be initialised with EITHER a
    distrorelease OR a distribution. This means you can specify either
    "package foo in ubuntu" or "package foo in warty", and then methods
    should work as expected.
    """

    implements(ISourcePackage)

    def __init__(self, sourcepackagename, distrorelease=None):
        """SourcePackage requires a SourcePackageName and a
        DistroRelease. These must be Launchpad database objects."""
        self.sourcepackagename = sourcepackagename
        self.distrorelease = distrorelease
        # set self.currentrelease based on current published sourcepackage
        # with this name in the distrorelease. if none is published, leave
        # self.currentrelease as None
        try:
            r = SourcePackageInDistro.selectBy(
                    sourcepackagenameID=sourcepackagename.id,
                    distroreleaseID = self.distrorelease.id)[0]
            self.currentrelease = SourcePackageRelease.get(r.id)
        except IndexError:
            # there is no published package in that distrorelease with this
            # name
            self.currentrelease = None

    def displayname(self):
        dn = ' the ' + self.sourcepackagename.name + ' source package in '
        dn += self.distrorelease.displayname
        return dn
    displayname = property(displayname)

    def title(self):
        titlestr = self.sourcepackagename.name
        titlestr += ' in ' + self.distribution.displayname
        titlestr += ' ' + self.distrorelease.displayname
        return titlestr
    title = property(title)

    shortdesc = "XXX this is a source package"

    description = "XXX this is still a source package"

    def distribution(self):
        return self.distrorelease.distribution
    distribution = property(distribution)

    def distro(self):
        return self.distribution
    distro = property(distro)

    def format(self):
        return self.currentrelease.format
    format = property(format)

    def changelog(self):
        return self.currentrelease.changelog
    changelog = property(changelog)

    def manifest(self):
        """For the moment, the manifest of a SourcePackage is defined as the
        manifest of the .currentrelease of that SourcePackage in the
        distrorelease. In future, we might have a separate table for the
        current working copy of the manifest for a source package."""
        return self.currentrelease.manifest
    manifest = property(manifest)

    def maintainer(self):
        querystr = "distribution = %i AND sourcepackagename = %i"
        querystr %= (self.distribution, self.sourcepackagename)
        return Maintainership.select(querystr)
    maintainer = property(maintainer)

    def releases(self):
        """For the moment, we will return all releases with the same name.
        Clearly, this is wrong, because it will mix different flavors of a
        sourcepackage as well as releases of entirely different
        sourcepackages (say, from RedHat and Ubuntu) that have the same
        name. Later, we want to use the PublishingMorgue table to get a
        proper set of sourcepackage releases specific to this
        distrorelease."""
        return SourcePackageRelease.select(
                SourcePackageRelease.q.sourcepackagenameID == self.sourcepackagename.id,
                orderBy=["version"]
                )
    releases = property(releases)

    products = RelatedJoin('Product', intermediateTable='Packaging')

    #
    # Properties
    #
    def name(self):
        return self.sourcepackagename.name
    name = property(name)

    def bugtasks(self):
        querystr = "distribution = %i AND sourcepackagename = %i"
        querystr %= (self.distribution, self.sourcepackagename)
        return BugTask.select(querystr)
    bugtasks = property(bugtasks)

    def potemplates(self):
        return POTemplate.selectBy(
                    distroreleaseID=self.distrorelease.id,
                    sourcepackagenameID=self.sourcepackagename.id)
    potemplates = property(potemplates)

    def potemplatecount(self):
        return self.potemplates.count()
    potemplatecount = property(potemplatecount)

    def product(self):
        try:
            clauseTables = ('Packaging', 'Product')
            querystr = ( "Product.id = Packaging.product AND "
                         "Packaging.sourcepackagename = %d AND "
                         "Packaging.distrorelease = %d" )
            querystr %= ( self.sourcepackagename.id,
                          self.distrorelease.id )
            return Product.select(querystr, clauseTables=clauseTables)[0]
        except IndexError:
            # No corresponding product
            return None
    product = property(product)

    def bugsCounter(self):
        from canonical.launchpad.database.bugtask import BugTask

        ret = [len(self.bugs)]
        severities = [
            BugSeverity.CRITICAL,
            BugSeverity.MAJOR,
            BugSeverity.NORMAL,
            BugSeverity.MINOR,
            BugSeverity.WISHLIST,
            BugTaskStatus.FIXED,
            BugTaskStatus.ACCEPTED,
        ]
        for severity in severities:
            n = BugTask.selectBy(severity=int(severity),
                                 sourcepackagenameID=self.sourcepackagename.id,
                                 distributionID=self.distribution.id).count()
            ret.append(n)
        return ret

    def getByVersion(self, version):
        """This will look for a sourcepackage with the given version in the
        distribution of this sourcepackage, NOT just the distrorelease of
        the sourcepackage. NB - this assumes that a given
        sourcepackagerelease version is UNIQUE in a distribution. This is
        true of Ubuntu, RedHat and similar distros, but might not be
        universally true."""
        ret = VSourcePackageReleasePublishing.selectBy(
                sourcepackagename=self.sourcepackagename,
                distribution=self.distribution,
                version=version)
        # XXX sabdfl 24/03/05 cprov: this will fail poorly if there is no 
        # source package release published in this distro, we need a clearer
        # plan for how to handle that failure
        assert ret.count() == 1
        return ret[0]

    def pendingrelease(self):
        ret = VSourcePackageReleasePublishing.selectBy(
                sourcepackagenameID=self.sourcepackagename.id,
                publishingstatus=PackagePublishingStatus.PENDING,
                distroreleaseID = self.distrorelease.id)
        if ret.count() == 0:
            return None
        return SourcePackageRelease.get(r[0].id)
    pendingrelease = property(pendingrelease)

    def publishedreleases(self):
        ret = VSourcePackageReleasePublishing.selectBy(
                sourcepackagenameID=self.sourcepackagename.id,
                publishingstatus=[PackagePublishingStatus.PUBLISHED,
                                  PackagePublishingStatus.SUPERSEDED],
                distroreleaseID = self.distrorelease.id)
        if ret.count() == 0:
            return None
        return list(ret)
    publishedreleases = property(publishedreleases)



class SourcePackageSet(object):
    """A set of Magic SourcePackage objects."""

    implements(ISourcePackageSet)

    def __init__(self, distribution=None, distrorelease=None):
        if distribution is not None and distrorelease is not None:
            if distrorelease.distribution is not distribution:
                raise TypeError, 'Must instantiate SourcePackageSet with distribution or distrorelease, not both'
        if distribution:
            self.distribution = distribution
            self.distrorelease = distribution.currentrelease
            self.title = distribution.title
        elif distrorelease:
            self.distribution = distrorelease.distribution
            self.distrorelease = distrorelease
            self.title = distrorelease.title
        else:
            self.title = ""
        self.title += " Source Packages"

    def __getitem__(self, name):
        try:
            spname = SourcePackageName.byName(name)
        except IndexError:
            raise KeyError, 'No source package name %s' % name
        return SourcePackage(sourcepackagename=spname,
                             distrorelease=self.distrorelease)

    def __iter__(self, text=None):
        querystr = self._querystr(text)
        for row in VSourcePackageReleasePublishing.select(querystr):
            yield row

    def _querystr(self, text=None):
        querystr = ''
        if self.distrorelease:
            querystr += 'distrorelease = %d' %  self.distrorelease 
        if text:
            if len(querystr):
                querystr += ' AND '
            querystr += "name ILIKE " + quote('%%' + text + '%%') 
        return querystr

    def query(self, text=None):
        querystr = self._querystr(text)
        for row in VSourcePackageReleasePublishing.select(querystr):
            yield SourcePackage(sourcepackagename=row.sourcepackagename,
                                distrorelease=row.distrorelease)

    def withBugs(self):
        pkgset = Set()
        results = BugTask.select(
            "distribution = %d AND sourcepackagename IS NOT NULL" % (
                self.distribution ) )
        for task in results:
            pkgset.add(task.sourcepackagename)

        return [SourcePackage(sourcepackagename=sourcepackagename,
                              distribution=self.distribution)
                    for sourcepackagename in pkgset]


