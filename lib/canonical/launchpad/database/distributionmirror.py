# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['DistributionMirror', 'MirrorDistroArchRelease',
           'MirrorDistroReleaseSource', 'MirrorProbeRecord']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, BoolCol, AND

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase

from canonical.lp.dbschema import (
    MirrorSpeed, MirrorContent, MirrorPulseType, MirrorStatus,
    PackagePublishingPocket, EnumCol)
from canonical.launchpad.interfaces import (
    IDistributionMirror, IMirrorDistroReleaseSource, IMirrorDistroArchRelease,
    IMirrorProbeRecord)


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

    def newMirrorArchRelease(self, distro_arch_release, pocket):
        """See IDistributionMirror"""
        return MirrorDistroArchRelease(
            pocket=pocket, distribution_mirror=self,
            distro_arch_release=distro_arch_release,
            status=MirrorStatus.UNKNOWN,)

    def newMirrorSourceRelease(self, distro_release):
        """See IDistributionMirror"""
        return MirrorDistroReleaseSource(
            distribution_mirror=self, distro_release=distro_release,
            status=MirrorStatus.UNKNOWN)

    @property
    def source_releases(self):
        """See IDistributionMirror"""
        return MirrorDistroReleaseSource.selectBy(distribution_mirrorID=self.id)

    @property
    def arch_releases(self):
        """See IDistributionMirror"""
        return MirrorDistroArchRelease.selectBy(distribution_mirrorID=self.id)


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
    status = EnumCol(
        notNull=True, schema=MirrorStatus)
    pocket = EnumCol(
        notNull=True, schema=PackagePublishingPocket)


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
    status = EnumCol(
        notNull=True, schema=MirrorStatus)


class MirrorProbeRecord(SQLBase):
    """See IMirrorProbeRecord"""

    implements(IMirrorProbeRecord)
    _table = 'MirrorProbeRecord'
    _defaultOrder = 'id'

    distribution_mirror = ForeignKey(
        dbName='distribution_mirror', foreignKey='DistributionMirror',
        notNull=True)
    log_file = ForeignKey(
        dbName='logfile', foreignKey='LibraryFileAlias')
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

