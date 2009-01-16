# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database class for table ArchiveSubscriber."""

__metaclass__ = type

__all__ = [
    'ArchiveSubscriber',
    ]

import pytz

from storm.locals import DateTime, Int, Reference, Storm, Unicode

from zope.interface import implements

from canonical.launchpad.interfaces.archivesubscriber import (
    IArchiveSubscriber)


class ArchiveSubscriber(Storm):
    """See `IArchiveSubscriber`."""
    implements(IArchiveSubscriber)
    __storm_table__ = 'ArchiveSubscriber'

    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    date_created = DateTime(
        name='date_created', allow_none=False, tzinfo=pytz.timezone('UTC'))

    subscriber_id = Int(name='subscriber', allow_none=False)
    subscriber = Reference(subscriber_id, 'Person.id')

    date_expires = DateTime(
        name='date_expires', allow_none=True, tzinfo=pytz.timezone('UTC'))

    status = Int(name='status', allow_none=False)

    description = Unicode(name='description', allow_none=True)

    date_cancelled = DateTime(
        name='date_cancelled', allow_none=True, tzinfo=pytz.timezone('UTC'))

    cancelled_by_id = Int(name='cancelled_by', allow_none=True)
    cancelled_by = Reference(cancelled_by_id, 'Person.id')
