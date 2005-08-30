# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SourcePackageRelease', 'SourcePackageReleaseSet']

import sets
from urllib2 import URLError

from zope.interface import implements
from zope.component import getUtility

from sqlobject import StringCol, ForeignKey, MultipleJoin

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp.dbschema import (
    EnumCol, SourcePackageUrgency, SourcePackageFormat)

from canonical.launchpad.interfaces import (ISourcePackageRelease,
    ISourcePackageReleaseSet)

from canonical.launchpad.database.binarypackage import BinaryPackage

from canonical.launchpad.database.build import Build
from canonical.launchpad.database.publishing import (
    SourcePackagePublishing)


class SourcePackageRelease(SQLBase):
    implements(ISourcePackageRelease)
    _table = 'SourcePackageRelease'

    section = ForeignKey(foreignKey='Section', dbName='section')
    creator = ForeignKey(foreignKey='Person', dbName='creator', notNull=True)
    component = ForeignKey(foreignKey='Component', dbName='component')
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
                                   dbName='sourcepackagename', notNull=True)
    maintainer = ForeignKey(foreignKey='Person', dbName='maintainer',
                            notNull=True)
    dscsigningkey = ForeignKey(foreignKey='GPGKey', dbName='dscsigningkey')
    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest')
    urgency = EnumCol(dbName='urgency', schema=SourcePackageUrgency,
                      notNull=True)
    dateuploaded = UtcDateTimeCol(dbName='dateuploaded', notNull=True,
                                  default=UTC_NOW)
    dsc = StringCol(dbName='dsc')
    version = StringCol(dbName='version', notNull=True)
    changelog = StringCol(dbName='changelog')
    builddepends = StringCol(dbName='builddepends')
    builddependsindep = StringCol(dbName='builddependsindep')
    architecturehintlist = StringCol(dbName='architecturehintlist')
    format = EnumCol(dbName='format',
                     schema=SourcePackageFormat,
                     default=SourcePackageFormat.DPKG,
                     notNull=True)
    uploaddistrorelease = ForeignKey(foreignKey='DistroRelease',
                                     dbName='uploaddistrorelease')

    builds = MultipleJoin('Build', joinColumn='sourcepackagerelease')
    files = MultipleJoin('SourcePackageReleaseFile',
                         joinColumn='sourcepackagerelease')

    @property
    def builds(self):
        return Build.selectBy(sourcepackagereleaseID=self.id,
            orderBy=['-datecreated'])

    @property
    def latest_build(self):
        builds = self.builds
        if len(builds) > 0:
            return builds[0]
        return None

    @property
    def name(self):
        return self.sourcepackagename.name

    @property
    def productrelease(self):
        """See ISourcePackageRelease."""
        series = None

        # Use any published source package to find the product series.
        # We can do this because if we ever find out that a source package
        # release in two product series, we've almost certainly got a data
        # problem there.
        publishings = SourcePackagePublishing.selectBy(
            sourcepackagereleaseID=self.id)
        for publishing in publishings:
            # imports us, so avoid circular import
            from canonical.launchpad.database.sourcepackage import \
                 SourcePackage
            sp = SourcePackage(self.sourcepackagename,
                               publishing.distrorelease)
            sp_series = sp.productseries
            if sp_series is not None:
                if series is None:
                    series = sp_series
                elif series != sp_series:
                    # XXX: we could warn about this --keybuk 22jun05
                    pass

        # No series -- no release
        if series is None:
            return None

        # XXX: find any release with the exact same version, or which
        # we begin with and after a dash.  We could be more intelligent
        # about this, but for now this will work for most. --keybuk 22jun05
        for release in series.releases:
            if release.version == self.version:
                return release
            elif self.version.startswith("%s-" % release.version):
                return release
        else:
            return None

    @property
    def binaries(self):
        clauseTables = ['SourcePackageRelease', 'BinaryPackage', 'Build']
        query = ('SourcePackageRelease.id = Build.sourcepackagerelease'
                 ' AND BinaryPackage.build = Build.id '
                 ' AND Build.sourcepackagerelease = %i' % self.id)
        return BinaryPackage.select(query, clauseTables=clauseTables)

    def architecturesReleased(self, distroRelease):
        # The import is here to avoid a circular import. See top of module.
        from canonical.launchpad.database.soyuz import DistroArchRelease
        clauseTables = ['PackagePublishing', 'BinaryPackage', 'Build']

        archReleases = sets.Set(DistroArchRelease.select(
            'PackagePublishing.distroarchrelease = DistroArchRelease.id '
            'AND DistroArchRelease.distrorelease = %d '
            'AND PackagePublishing.binarypackage = BinaryPackage.id '
            'AND BinaryPackage.build = Build.id '
            'AND Build.sourcepackagerelease = %d'
            % (distroRelease.id, self.id),
            clauseTables=clauseTables))
        return archReleases


class SourcePackageReleaseSet:

    implements(ISourcePackageReleaseSet)

    def getByCreatorID(self, personID):
        querystr = """sourcepackagerelease.creator = %d AND
                      sourcepackagerelease.sourcepackagename = 
                        sourcepackagename.id""" % personID
        return SourcePackageRelease.select(
            querystr,
            orderBy='SourcePackageName.name',
            clauseTables=['SourcePackageRelease', 'SourcePackageName'])

