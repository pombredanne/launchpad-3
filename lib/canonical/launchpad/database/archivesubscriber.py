# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database class for table ArchiveSubscriber."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscriber',
    ]

import pytz

from storm.locals import DateTime, Int, Reference, Store, Storm, Unicode

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.archivesubscriber import (
    ArchiveSubscriberStatus, IArchiveSubscriber)


class ArchiveSubscriber(Storm):
    """See `IArchiveSubscriber`."""
    implements(IArchiveSubscriber)
    __storm_table__ = 'ArchiveSubscriber'

    id = Int(primary=True)

    archiveID = Int(name='archive', allow_none=False)
    archive = Reference(archiveID, 'Archive.id')

    registrantID = Int(name='registrant', allow_none=False)
    registrant = Reference(registrantID, 'Person.id')

    date_created = DateTime(
        name='date_created', allow_none=False, tzinfo=pytz.UTC)

    subscriberID = Int(name='subscriber', allow_none=False)
    subscriber = Reference(subscriberID, 'Person.id')

    date_expires = DateTime(
        name='date_expires', allow_none=True, tzinfo=pytz.UTC)

    status = DBEnum(
        name='status', allow_none=False,
        enum=ArchiveSubscriberStatus)

    description = Unicode(name='description', allow_none=True)

    date_cancelled = DateTime(
        name='date_cancelled', allow_none=True, tzinfo=pytz.UTC)

    cancelled_byID = Int(name='cancelled_by', allow_none=True)
    cancelled_by = Reference(cancelled_byID, 'Person.id')

    def cancel(self, cancelled_by):
        """See `IArchiveSubscriber`."""
        self.date_cancelled = UTC_NOW
        self.cancelled_by = cancelled_by
        self.status = ArchiveSubscriberStatus.CANCELLED


class ArchiveSubscriberSet:
    """See `IArchiveSubscriberSet`."""

    def getBySubscriber(self, subscriber, archive=None, active_only=True):
        """See `IArchiveSubscriberSet`."""
        extra_exprs = []
        if archive:
            extra_exprs.append(ArchiveSubscriber.archive == archive)

        if active_only:
            extra_exprs.append(
                ArchiveSubscriber.status == ArchiveSubscriberStatus.ACTIVE)

        store = Store.of(subscriber)
        return store.find(
            ArchiveSubscriber,
            ArchiveSubscriber.subscriber == subscriber,
            *extra_exprs)

    def getByArchive(self, archive, active_only=True):
        """See `IArchiveSubscriberSet`."""
        extra_exprs = []

        if active_only:
            extra_exprs.append(
                ArchiveSubscriber.status == ArchiveSubscriberStatus.ACTIVE)

        store = Store.of(archive)
        return store.find(
            ArchiveSubscriber,
            ArchiveSubscriber.archive == archive,
            *extra_exprs)
