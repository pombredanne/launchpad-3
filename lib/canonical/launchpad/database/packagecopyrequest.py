# Copyright 2004-2008 Canonical Ltd.  All rights reserved.


__metaclass__ = type
__all__ = ['PackageCopyRequest', 'PackageCopyRequestSet']


from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces.packagecopyrequest import (
    PackageCopyStatus, IPackageCopyRequest, IPackageCopyRequestSet)
from canonical.launchpad.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.validators.person import validate_public_person
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)

from sqlobject import BoolCol, ForeignKey, StringCol


class PackageCopyRequest(SQLBase):
    implements(IPackageCopyRequest)
    _table = 'PackageCopyRequest'
    _defaultOrder = 'id'

    target_archive = ForeignKey(foreignKey='Archive', notNull=True)
    target_distroseries = ForeignKey(foreignKey='DistroSeries', notNull=False)
    target_component = ForeignKey(foreignKey='Component', notNull=False)
    target_pocket = EnumCol(schema=PackagePublishingPocket, notNull=False)

    copy_binaries = BoolCol(notNull=True, default=False)

    source_archive = ForeignKey(foreignKey='Archive', notNull=True)
    source_distroseries = ForeignKey(foreignKey='DistroSeries', notNull=False)
    source_component = ForeignKey(foreignKey='Component', notNull=False)
    source_pocket = EnumCol(schema=PackagePublishingPocket, notNull=False)

    requester = ForeignKey(
        foreignKey='Person', notNull=True,
        storm_validator=validate_public_person)

    status = EnumCol(schema=PackageCopyStatus, notNull=True)
    reason = StringCol(notNull=False)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_started = UtcDateTimeCol(notNull=False)
    date_completed = UtcDateTimeCol(notNull=False)

    def __str__(self):
        """See `IPackageCopyRequest`"""

        def get_name_or_nothing(property_name, nothing_indicator='-'):
            property = getattr(self, property_name, None)

            # Return straight-away if property is not set.
            if property is None:
                return nothing_indicator

            # Does the property have a name?
            name = getattr(property, 'name', None)
            if name is not None:
                return name

            # Does the property have a title?
            title = getattr(property, 'title', None)
            if title is not None:
                return title

            # Return the string representation of the property as a last
            # resort.
            return str(property)

        result = (
            "Package copy request\n"
            "source = %s/%s/%s/%s\ntarget = %s/%s/%s/%s\n"
            "copy binaries: %s\nrequester: %s\nstatus: %s\n"
            "date created: %s\ndate started: %s\ndate completed: %s" %
            (get_name_or_nothing('source_archive'),
             get_name_or_nothing('source_distroseries'),
             get_name_or_nothing('source_component'),
             get_name_or_nothing('source_pocket'),
             get_name_or_nothing('target_archive'),
             get_name_or_nothing('target_distroseries'),
             get_name_or_nothing('target_component'),
             get_name_or_nothing('target_pocket'),
             get_name_or_nothing('copy_binaries'),
             get_name_or_nothing('requester'),
             get_name_or_nothing('status'),
             get_name_or_nothing('date_created'),
             get_name_or_nothing('date_started'),
             get_name_or_nothing('date_completed')))
        return result

    def markAsInprogress(self):
        """See `IPackageCopyRequest`"""
        self.status = PackageCopyStatus.INPROGRESS
        self.date_started = UTC_NOW

    def markAsComplete(self):
        """See `IPackageCopyRequest`"""
        self.status = PackageCopyStatus.COMPLETE
        self.date_completed = UTC_NOW

    def markAsFailed(self):
        """See `IPackageCopyRequest`"""
        self.status = PackageCopyStatus.FAILED
        self.date_completed = UTC_NOW

    def markAsCanceling(self):
        """See `IPackageCopyRequest`"""
        self.status = PackageCopyStatus.CANCELING

    def markAsCancelled(self):
        """See `IPackageCopyRequest`"""
        self.status = PackageCopyStatus.CANCELLED
        self.date_completed = UTC_NOW


class PackageCopyRequestSet:
    implements(IPackageCopyRequestSet)

    def new(
        self, source, target, requester, copy_binaries=False, reason=None):
        """See `IPackageCopyRequestSet`"""
        return PackageCopyRequest(
            target_archive=target.archive,
            target_distroseries=target.distroseries,
            target_component=target.component,
            target_pocket=target.pocket,
            copy_binaries=copy_binaries,
            source_archive=source.archive,
            source_distroseries=source.distroseries,
            source_component=source.component,
            source_pocket=source.pocket,
            requester=requester,
            status=PackageCopyStatus.NEW,
            reason=reason)

    def getByPersonAndStatus(self, requester, status=None):
        """See `IPackageCopyRequestSet`"""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        base_clauses = (PackageCopyRequest.requester == requester,)
        if status is not None:
            optional_clauses = (PackageCopyRequest.status == status,)
        else:
            optional_clauses = ()
        return store.find(
            PackageCopyRequest, *(base_clauses + optional_clauses))

    def getByTargetDistroSeries(self, distroseries):
        """See `IPackageCopyRequestSet`"""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            PackageCopyRequest,
            PackageCopyRequest.target_distroseries == distroseries)

    def getBySourceDistroSeries(self, distroseries):
        """See `IPackageCopyRequestSet`"""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            PackageCopyRequest,
            PackageCopyRequest.source_distroseries == distroseries)

    def getByTargetArchive(self, archive):
        """See `IPackageCopyRequestSet`"""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            PackageCopyRequest,
            PackageCopyRequest.target_archive == archive)
