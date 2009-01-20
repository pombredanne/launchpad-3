# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database class for table ArchiveSubscriber."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscriber',
    ]

import pytz

from storm.locals import DateTime, Int, Reference, Storm, Unicode

from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.archivesubscriber import (
    ArchiveSubscriberStatus, IArchiveSubscriber)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


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
        name='date_created', allow_none=False, tzinfo=pytz.timezone('UTC'))

    subscriberID = Int(name='subscriber', allow_none=False)
    subscriber = Reference(subscriberID, 'Person.id')

    date_expires = DateTime(
        name='date_expires', allow_none=True, tzinfo=pytz.timezone('UTC'))

    status = DBEnum(
        name='status', allow_none=False,
        enum=ArchiveSubscriberStatus)

    description = Unicode(name='description', allow_none=True)

    date_cancelled = DateTime(
        name='date_cancelled', allow_none=True, tzinfo=pytz.timezone('UTC'))

    cancelled_byID = Int(name='cancelled_by', allow_none=True)
    cancelled_by = Reference(cancelled_byID, 'Person.id')

    def cancel(self, cancelled_by):
        """See `IArchiveSubscriber`."""
        self.date_cancelled = UTC_NOW
        self.cancelled_by = cancelled_by
        self.status = ArchiveSubscriberStatus.CANCELLED


class ArchiveSubscriberSet:
    """See `IArchiveSubscriberSet`."""

    def getBySubscriber(self, subscriber):
        """See `IArchiveSubscriberSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            ArchiveSubscriber,
            ArchiveSubscriber.subscriber == subscriber)

    def getByArchive(self, archive):
        """See `IArchiveSubscriberSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            ArchiveSubscriber,
            ArchiveSubscriber.archive == archive)

