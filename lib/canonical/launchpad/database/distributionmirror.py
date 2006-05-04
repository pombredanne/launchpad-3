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

from canonical.config import config
from canonical.cachedproperty import cachedproperty
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.archivepublisher.publishing import pocketsuffix
from canonical.archivepublisher.pool import Poolifier
from canonical.lp.dbschema import (
    MirrorSpeed, MirrorContent, MirrorPulseType, MirrorStatus,
    PackagePublishingPocket, EnumCol, PackagePublishingStatus,
    SourcePackageFileType, BinaryPackageFileType)
from canonical.launchpad.interfaces import (
    IDistributionMirror, IMirrorDistroReleaseSource, IMirrorDistroArchRelease,
    IMirrorProbeRecord, IDistributionMirrorSet, PROBE_INTERVAL,
    IDistroRelease, IDistroArchRelease)
from canonical.launchpad.database.files import (
    BinaryPackageFile, SourcePackageReleaseFile)
from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory, SecureBinaryPackagePublishingHistory)
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.webapp import urlappend
from canonical.launchpad.mail import simple_sendmail, format_address


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

    @cachedproperty
    def last_probe_record(self):
        """See IDistributionMirror"""
        return MirrorProbeRecord.selectFirst(
            MirrorProbeRecord.q.distribution_mirrorID==self.id,
            orderBy='-date_created')

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
        template = get_email_template('notify-mirror-owner.txt')
        fromaddress = format_address(
            "Launchpad Mirror Prober", config.noreply_from_address)

        replacements = {'distro': self.distribution.title,
                        'mirror_name': self.name}
        message = template % replacements

        subject = "Launchpad: Your distribution mirror seems to be unreachable"
        to_address = format_address(
            self.owner.displayname, self.owner.preferredemail.email)
        simple_sendmail(fromaddress, to_address, subject, message)

    def newProbeRecord(self, log_file):
        """See IDistributionMirror"""
        return MirrorProbeRecord(distribution_mirror=self, log_file=log_file)

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
        assert IDistroArchRelease.providedBy(distro_arch_release)
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
        assert IDistroRelease.providedBy(distro_release)
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
                AND distributionmirror.content = %s
            GROUP BY distributionmirror.id
            HAVING max(mirrorproberecord.date_created) IS NULL
                OR max(mirrorproberecord.date_created) 
                    < %s - '%s hours'::interval
            """ % (MirrorContent.ARCHIVE, UTC_NOW, PROBE_INTERVAL)
        conn = DistributionMirror._connection
        ids = ", ".join(str(id) for (id, date_created) in conn.queryAll(query))
        query = '1 = 2'
        if ids:
            query = 'id IN (%s)' % ids
        return DistributionMirror.select(query)


class _MirrorReleaseMixIn:
    """A class containing some commonalities between MirrorDistroArchRelease
    and MirrorDistroReleaseSource.

    This class is not meant to be used alone. Instead, both
    MirrorDistroReleaseSource and MirrorDistroArchRelease should inherit from
    it and override the methods and attributes that say so.
    """

    status_times = [
        (MirrorStatus.UP, 0.5),
        (MirrorStatus.ONEHOURBEHIND, 1.5),
        (MirrorStatus.TWOHOURSBEHIND, 2.5),
        (MirrorStatus.SIXHOURSBEHIND, 6.5),
        (MirrorStatus.ONEDAYBEHIND, 24.5),
        (MirrorStatus.TWODAYSBEHIND, 48.5),
        (MirrorStatus.ONEWEEKBEHIND, 168.5)
        ]

    # The class where we search for the history of packages published. Must be
    # overwritten in subclasses.
    _publishing_class = None

    @property
    def _base_query(self):
        """The base query to be used when searching for published packages.

        Must be overwritten in subclasses.
        """
        raise NotImplementedError

    def _getPackageReleaseURLFromPublishingRecord(self, publishing_record):
        """Given a publishing record, return a dictionary mapping MirrorStatus
        items to URLs of files on this mirror.

        Must be overwritten on subclasses.
        """
        raise NotImplementedError

    @property
    def _no_published_uploads_msg(self):
        """A message to be logged when no publishing records are found for
        this (mirror,component,pocket) tuple.

        Must be overwritten on subclasses.
        """
        raise NotImplementedError

    def getURLsToCheckUpdateness(self, when=None):
        """See IMirrorDistroReleaseSource or IMirrorDistroArchRelease."""
        base_query = self._base_query
        publishing_class = self._publishing_class
        assert base_query is not None and publishing_class is not None

        if when is None:
            when = datetime.now(pytz.timezone('UTC'))
            
        # Check if there was any recent upload on this distro release.
        status, threshold = self.status_times[-1]
        oldest_status_time = when - timedelta(hours=threshold)
        query = (base_query + " AND datepublished > %s" 
                 % sqlvalues(oldest_status_time))
        recent_upload = publishing_class.selectFirst(
            query, orderBy='-datepublished')
        if not recent_upload:
            # No recent uploads, so we only need the URL of the last package
            # uploaded here. If that URL is accessible, we know the mirror is
            # up-to-date. Otherwise we mark it as UNKNOWN.
            latest_upload = publishing_class.selectFirst(
                base_query, orderBy='-datepublished')

            if latest_upload is None:
                # This should not happen when running on production because
                # the publishing records are correctly filled. But that's not
                # true when it comes to our sampledata.
                # XXX: This will actually happen in production, and when it
                # happens it's probably not a good idea to return an empty
                # dictionary, as this will in fact make this mirror's status
                # be UNKNOWN when it's actually UPTODATE.
                # -- Guilherme Salgado, 2006-04-27
                return {}

            url = self._getPackageReleaseURLFromPublishingRecord(
                latest_upload)
            return {MirrorStatus.UP: url}

        urls = {}
        last_threshold = timedelta()
        for status, threshold in self.status_times:
            end = when - last_threshold
            start = when - timedelta(hours=threshold)
            last_threshold = timedelta(hours=threshold)

            query = (base_query + " AND datepublished BETWEEN %s AND %s"
                     % sqlvalues(start, end))
            upload = publishing_class.selectFirst(
                query, orderBy='-datepublished')

            if upload is None:
                # No uploads that would allow us to know the mirror was in
                # this status, so we better skip it.
                continue

            url = self._getPackageReleaseURLFromPublishingRecord(upload)
            urls.update({status: url})

        return urls


class MirrorDistroArchRelease(SQLBase, _MirrorReleaseMixIn):
    """See IMirrorDistroArchRelease"""

    implements(IMirrorDistroArchRelease)
    _table = 'MirrorDistroArchRelease'
    _defaultOrder = 'id'
    _publishing_class = SecureBinaryPackagePublishingHistory

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

    @property
    def _no_published_uploads_msg(self):
        return ("No published uploads were found for DistroArchRelease "
                "'%s %s', Pocket '%s' and Component '%s'" 
                % (self.distro_arch_release.distrorelease.name,
                   self.distro_arch_release.architecturetag,
                   self.pocket.name, self.component.name))

    @property
    def _base_query(self):
        """The base query to search for entries in
        SecureBinaryPackagePublishingHistory that refer to the 
        distroarchrelease, pocket and component of this mirror.
        """
        return """
            pocket = %s AND component = %s AND distroarchrelease = %s
            AND status = %s
            """ % sqlvalues(self.pocket, self.component.id, 
                            self.distro_arch_release.id,
                            PackagePublishingStatus.PUBLISHED)

    def _getPackageReleaseURLFromPublishingRecord(self, publishing_record):
        """Given a SecureBinaryPackagePublishingHistory, return the URL on 
        this mirror from where the BinaryPackageRelease file can be downloaded.
        """
        bpr = publishing_record.binarypackagerelease
        base_url = self.distribution_mirror.http_base_url
        path = Poolifier().poolify(bpr.sourcepackagename, self.component.name)
        file = BinaryPackageFile.selectOneBy(
            binarypackagereleaseID=bpr.id, filetype=BinaryPackageFileType.DEB)
        full_path = 'pool/%s/%s' % (path, file.libraryfile.filename)
        return urlappend(base_url, full_path)


class MirrorDistroReleaseSource(SQLBase, _MirrorReleaseMixIn):
    """See IMirrorDistroReleaseSource"""

    implements(IMirrorDistroReleaseSource)
    _table = 'MirrorDistroReleaseSource'
    _defaultOrder = 'id'
    _publishing_class = SecureSourcePackagePublishingHistory

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

    @property
    def _no_published_uploads_msg(self):
        return ("No published uploads were found for DistroRelease "
                "'%s, Pocket '%s' and Component '%s'" 
                % (self.distro_release.name, self.pocket.name, 
                   self.component.name))

    @property
    def _base_query(self):
        """The base query to search for entries in
        SecureSourcePackagePublishingHistory that refer to the distrorelease,
        pocket and component of this mirror.
        """
        return """
            pocket = %s AND component = %s AND distrorelease = %s
            AND status = %s
            """ % sqlvalues(self.pocket, self.component.id, 
                            self.distro_release.id,
                            PackagePublishingStatus.PUBLISHED)

    def _getPackageReleaseURLFromPublishingRecord(self, publishing_record):
        """Given a SecureSourcePackagePublishingHistory, return the URL on 
        this mirror from where the SourcePackageRelease file can be downloaded.
        """
        spr = publishing_record.sourcepackagerelease
        base_url = self.distribution_mirror.http_base_url
        sourcename = spr.name
        path = Poolifier().poolify(sourcename, self.component.name)
        file = SourcePackageReleaseFile.selectOneBy(
            sourcepackagereleaseID=spr.id, filetype=SourcePackageFileType.DSC)
        full_path = 'pool/%s/%s' % (path, file.libraryfile.filename)
        return urlappend(base_url, full_path)


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

