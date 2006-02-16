# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['DistributionMirror', 'MirrorDistroArchRelease',
           'MirrorDistroReleaseSource', 'MirrorProbeRecord',
           'DistributionMirrorSet']

from datetime import datetime, timedelta
import pytz
import warnings

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, BoolCol

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.archivepublisher.publishing import pocketsuffix
from canonical.archivepublisher.pool import Poolifier
from canonical.lp.dbschema import (
    MirrorSpeed, MirrorContent, MirrorPulseType, MirrorStatus,
    PackagePublishingPocket, EnumCol, PackagePublishingStatus)
from canonical.launchpad.interfaces import (
    IDistributionMirror, IMirrorDistroReleaseSource, IMirrorDistroArchRelease,
    IMirrorProbeRecord, IDistributionMirrorSet, PROBE_INTERVAL)
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory, SecureBinaryPackagePublishingHistory)
from canonical.launchpad.helpers import getBinaryPackageExtension


class DistributionMirror(SQLBase):
    """See IDistributionMirror"""

    implements(IDistributionMirror)
    _table = 'DistributionMirror'
    _defaultOrder = 'id'

    owner = ForeignKey(
        dbName='owner', foreignKey='Person', notNull=True)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=True)
    name = StringCol(
        alternateID=True, notNull=True)
    displayname = StringCol(
        notNull=False, default=None)
    description = StringCol(
        notNull=False, default=None)
    http_base_url = StringCol(
        notNull=False, default=None, unique=True)
    ftp_base_url = StringCol(
        notNull=False, default=None, unique=True)
    rsync_base_url = StringCol(
        notNull=False, default=None, unique=True)
    pulse_source = StringCol(
        notNull=False, default=None)
    enabled = BoolCol(
        notNull=True, default=False)
    file_list = ForeignKey(
        dbName='file_list', foreignKey='LibraryFileAlias')
    speed = EnumCol(
        notNull=True, schema=MirrorSpeed)
    country = ForeignKey(
        dbName='country', foreignKey='Country', notNull=True)
    content = EnumCol(
        notNull=True, schema=MirrorContent)
    pulse_type = EnumCol(
        notNull=True, schema=MirrorPulseType)
    official_candidate = BoolCol(
        notNull=True, default=False)
    official_approved = BoolCol(
        notNull=True, default=False)

    @property
    def title(self):
        """See IDistributionMirror"""
        if self.displayname:
            return self.displayname
        else:
            return self.name

    def isOfficial(self):
        """See IDistributionMirror"""
        return self.official_candidate and self.official_approved

    def disableAndNotifyOwner(self):
        """See IDistributionMirror"""
        self.enabled = False
        # XXX: Missing a call to simple_sendmail to notify the owner.
        # -- Guilherme Salgado, 2006-02-16

    def newProbeRecord(self):
        """See IDistributionMirror"""
        return MirrorProbeRecord(distribution_mirror=self)

    def deleteMirrorDistroArchRelease(self, distro_arch_release, pocket,
                                      component):
        """See IDistributionMirror"""
        mirror = MirrorDistroArchRelease.selectOneBy(
            distribution_mirrorID=self.id,
            distro_arch_releaseID=distro_arch_release.id,
            pocket=pocket, componentID=component.id)
        if mirror is not None:
            mirror.destroySelf()

    def ensureMirrorDistroArchRelease(self, distro_arch_release, pocket,
                                      component):
        """See IDistributionMirror"""
        mirror = MirrorDistroArchRelease.selectOneBy(
            distribution_mirrorID=self.id,
            distro_arch_releaseID=distro_arch_release.id,
            pocket=pocket, componentID=component.id)
        if mirror is None:
            mirror = MirrorDistroArchRelease(
                pocket=pocket, distribution_mirror=self,
                distro_arch_release=distro_arch_release,
                componentID=component.id)
        return mirror

    def ensureMirrorDistroReleaseSource(self, distro_release, pocket,
                                        component):
        """See IDistributionMirror"""
        mirror = MirrorDistroReleaseSource.selectOneBy(
            distribution_mirrorID=self.id, distro_releaseID=distro_release.id,
            pocket=pocket, componentID=component.id)
        if mirror is None:
            mirror = MirrorDistroReleaseSource(
                distribution_mirror=self, distro_release=distro_release,
                pocket=pocket, componentID=component.id)
        return mirror

    def deleteMirrorDistroReleaseSource(self, distro_release, pocket,
                                        component):
        """See IDistributionMirror"""
        mirror = MirrorDistroReleaseSource.selectOneBy(
            distribution_mirrorID=self.id, distro_releaseID=distro_release.id,
            pocket=pocket, componentID=component.id)
        if mirror is not None:
            mirror.destroySelf()

    @property
    def source_releases(self):
        """See IDistributionMirror"""
        return MirrorDistroReleaseSource.selectBy(distribution_mirrorID=self.id)

    @property
    def arch_releases(self):
        """See IDistributionMirror"""
        return MirrorDistroArchRelease.selectBy(distribution_mirrorID=self.id)

    def guessPackagesPaths(self):
        """See IDistributionMirror"""
        paths = []
        for release in self.distribution.releases:
            for pocket, suffix in pocketsuffix.items():
                for component in release.components:
                    for arch_release in release.architectures:
                        path = ('dists/%s%s/%s/binary-%s/Packages.gz'
                                % (release.name, suffix, component.name,
                                   arch_release.architecturetag))
                        paths.append((arch_release, pocket, component, path))
        return paths

    def guessSourcesPaths(self):
        """See IDistributionMirror"""
        paths = []
        for release in self.distribution.releases:
            for pocket, suffix in pocketsuffix.items():
                for component in release.components:
                    path = ('dists/%s%s/%s/source/Sources.gz'
                            % (release.name, suffix, component.name))
                    paths.append((release, pocket, component, path))
        return paths


class DistributionMirrorSet:
    """See IDistributionMirrorSet"""

    implements (IDistributionMirrorSet)

    def __getitem__(self, mirror_id):
        """See IDistributionMirrorSet"""
        return DistributionMirror.get(mirror_id)

    def getMirrorsToProbe(self):
        """See IDistributionMirrorSet"""
        query = """
            SELECT distributionmirror.id, max(mirrorproberecord.date_created)
            FROM distributionmirror 
            LEFT OUTER JOIN mirrorproberecord
                ON mirrorproberecord.distribution_mirror = distributionmirror.id
            WHERE distributionmirror.enabled IS TRUE
            GROUP BY distributionmirror.id
            HAVING max(mirrorproberecord.date_created) IS NULL
                OR max(mirrorproberecord.date_created) 
                    < %s - '%s hours'::interval
            """ % (UTC_NOW, PROBE_INTERVAL)
        conn = DistributionMirror._connection
        ids = ", ".join(str(id) for (id, date_created) in conn.queryAll(query))
        query = '1 = 2'
        if ids:
            query = 'id IN (%s)' % ids
        return DistributionMirror.select(query)


STATUS_TIMES = {
    MirrorStatus.UP: (0, 0.5),
    MirrorStatus.ONEHOURBEHIND: (0.51, 1.5),
    MirrorStatus.TWOHOURSBEHIND: (1.51, 2.5),
    MirrorStatus.SIXHOURSBEHIND: (2.51, 6.5),
    MirrorStatus.ONEDAYBEHIND: (6.51, 24.5),
    MirrorStatus.TWODAYSBEHIND: (24.51, 48.5),
    MirrorStatus.ONEWEEKBEHIND: (48.51, 168.5)
    }


class MirrorDistroArchRelease(SQLBase):
    """See IMirrorDistroArchRelease"""

    implements(IMirrorDistroArchRelease)
    _table = 'MirrorDistroArchRelease'
    _defaultOrder = 'id'

    distribution_mirror = ForeignKey(
        dbName='distribution_mirror', foreignKey='DistributionMirror',
        notNull=True)
    distro_arch_release = ForeignKey(
        dbName='distro_arch_release', foreignKey='DistroArchRelease',
        notNull=True)
    component = ForeignKey(
        dbName='component', foreignKey='Component', notNull=True)
    status = EnumCol(
        notNull=True, default=MirrorStatus.UNKNOWN, schema=MirrorStatus)
    pocket = EnumCol(
        notNull=True, schema=PackagePublishingPocket)

    def _getBinaryPackageReleaseURL(self, binary_package_release):
        """Given a BinaryPackageRelease, return the URL on this mirror from
        where that BinaryPackageRelease file can be downloaded.
        """
        bpr = binary_package_release
        base_url = self.distribution_mirror.http_base_url
        path = Poolifier().poolify(bpr.sourcepackagename, self.component.name)
        name = '%s_%s_' % (bpr.name, bpr.version)
        if bpr.architecturespecific:
            name += bpr.build.distroarchrelease.architecturetag
        else:
            name += 'all'
        name += getBinaryPackageExtension(bpr.binpackageformat)
        return '%s/pool/%s/%s' % (base_url, path, name)

    def getURLsToCheckUpdateness(self, when=None):
        """Return a dictionary mapping each different MirrorStatus to a URL on
        this mirror.

        These URLs should be checked and, if they are accessible, we know
        that's the current status of this mirror.
        """
        now = datetime.now(pytz.timezone('UTC'))
        if when is not None:
            now = when
            
        base_query = """
            pocket = %s AND component = %s AND distroarchrelease = %s
            AND status = %s
            """ % sqlvalues(self.pocket, self.component.id, 
                            self.distro_arch_release.id,
                            PackagePublishingStatus.PUBLISHED)

        # Check if there was any recent upload on this distro release.
        status, interval = STATUS_TIMES.items()[-1]
        oldest_status_time = now - timedelta(hours=interval[1])
        query = (base_query + " AND datepublished > %s" 
                 % sqlvalues(oldest_status_time))
        recent_uploads = SecureBinaryPackagePublishingHistory.select(
            query, limit=1)
        if not recent_uploads:
            # No recent uploads, so we only need the URL of the last package
            # uploaded here. If that URL is accessible, we know the mirror is
            # up-to-date. Otherwise we mark it as UNKNOWN.
            results = SecureBinaryPackagePublishingHistory.select(
                base_query, orderBy='-datepublished', limit=1)

            if not results:
                # This should not happen when running on production because
                # the publishing records are correctly filled. But that's not
                # true when it comes to our sampledata.
                warnings.warn(
                    "No published uploads were found for DistroArchRelease "
                    "'%s %s', Pocket '%s' and Component '%s'" 
                    % (self.distro_arch_release.distrorelease.name,
                       self.distro_arch_release.architecturetag,
                       self.pocket.name, self.component.name))
                return {}

            assert results.count() == 1
            sourcepackagerelease = results[0].binarypackagerelease
            url = self._getBinaryPackageReleaseURL(sourcepackagerelease)
            return {MirrorStatus.UP: url}

        urls = {}
        for status, interval in STATUS_TIMES.items():
            end, start = interval
            start = now - timedelta(hours=start)
            end = now - timedelta(hours=end)

            query = (base_query + " AND datepublished BETWEEN %s AND %s"
                     % sqlvalues(start, end))
            results = SecureBinaryPackagePublishingHistory.select(
                query, orderBy='-datepublished', limit=1)

            if not results:
                # No uploads that would allow us to know the mirror was in
                # this status, so we better skip it.
                continue

            assert results.count() == 1
            item = results[0]
            url = self._getBinaryPackageReleaseURL(item.binarypackagerelease)
            urls.update({status: url})

        return urls


class MirrorDistroReleaseSource(SQLBase):
    """See IMirrorDistroReleaseSource"""

    implements(IMirrorDistroReleaseSource)
    _table = 'MirrorDistroReleaseSource'
    _defaultOrder = 'id'

    distribution_mirror = ForeignKey(
        dbName='distribution_mirror', foreignKey='DistributionMirror',
        notNull=True)
    distro_release = ForeignKey(
        dbName='distro_release', foreignKey='DistroRelease',
        notNull=True)
    component = ForeignKey(
        dbName='component', foreignKey='Component', notNull=True)
    status = EnumCol(
        notNull=True, default=MirrorStatus.UNKNOWN, schema=MirrorStatus)
    pocket = EnumCol(
        notNull=True, schema=PackagePublishingPocket)

    def _getSourcePackageReleaseDscURL(self, source_package_release):
        """Given a SourcePackageRelease, return the URL on this mirror from
        where that SourcePackageRelease's dsc file can be downloaded.
        """
        base_url = self.distribution_mirror.http_base_url
        sourcename = source_package_release.name
        path = Poolifier().poolify(sourcename, self.component.name)
        version = source_package_release.version
        return '%s/pool/%s/%s_%s.dsc' % (base_url, path, sourcename, version)

    # XXX: Yes, this method is almost identical to its MirrorDistroArchRelease
    # variant. I'm going to refactor them before merging this, but I can't do
    # it right now.
    # -- Guilherme Salgado, 2006-02-15
    def getURLsToCheckUpdateness(self, when=None):
        """Return a dictionary mapping each different MirrorStatus to a URL on
        this mirror.

        These URLs should be checked and, if they are accessible, we know
        that's the current status of this mirror.
        """
        now = datetime.now(pytz.timezone('UTC'))
        if when is not None:
            now = when
            
        base_query = """
            pocket = %s AND component = %s AND distrorelease = %s
            AND status = %s
            """ % sqlvalues(self.pocket, self.component.id, 
                            self.distro_release.id,
                            PackagePublishingStatus.PUBLISHED)

        # Check if there was any recent upload on this distro release.
        status, interval = STATUS_TIMES.items()[-1]
        oldest_status_time = now - timedelta(hours=interval[1])
        query = (base_query + " AND datepublished > %s" 
                 % sqlvalues(oldest_status_time))
        recent_uploads = SecureSourcePackagePublishingHistory.select(
            query, limit=1)
        if not recent_uploads:
            # No recent uploads, so we only need the URL of the last package
            # uploaded here. If that URL is accessible, we know the mirror is
            # up-to-date. Otherwise we mark it as UNKNOWN.
            results = SecureSourcePackagePublishingHistory.select(
                base_query, orderBy='-datepublished', limit=1)

            if not results:
                # This should not happen when running on production because
                # the publishing records are correctly filled. But that's not
                # true when it comes to our sampledata.
                warnings.warn(
                    "No published uploads were found for DistroRelease '%s', "
                    "Pocket '%s' and Component '%s'" 
                    % (self.distro_release.name, self.pocket.name,
                       self.component.name))
                return {}

            assert results.count() == 1
            sourcepackagerelease = results[0].sourcepackagerelease
            url = self._getSourcePackageReleaseDscURL(sourcepackagerelease)
            return {MirrorStatus.UP: url}

        urls = {}
        for status, interval in STATUS_TIMES.items():
            end, start = interval
            start = now - timedelta(hours=start)
            end = now - timedelta(hours=end)

            query = (base_query + " AND datepublished BETWEEN %s AND %s"
                     % sqlvalues(start, end))
            results = SecureSourcePackagePublishingHistory.select(
                query, orderBy='-datepublished', limit=1)

            if not results:
                # No uploads that would allow us to know the mirror was in
                # this status, so we better skip it.
                continue

            assert results.count() == 1
            item = results[0]
            url = self._getSourcePackageReleaseDscURL(item.sourcepackagerelease)
            urls.update({status: url})

        return urls


class MirrorProbeRecord(SQLBase):
    """See IMirrorProbeRecord"""

    implements(IMirrorProbeRecord)
    _table = 'MirrorProbeRecord'
    _defaultOrder = 'id'

    distribution_mirror = ForeignKey(
        dbName='distribution_mirror', foreignKey='DistributionMirror',
        notNull=True)
    log_file = ForeignKey(
        dbName='log_file', foreignKey='LibraryFileAlias', default=None)
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

