# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database class for table ArchiveAuthToken."""

__metaclass__ = type

__all__ = [
    'ArchiveAuthToken',
    ]

import pytz

from storm.locals import DateTime, Int, RawStr, Reference, Storm

from zope.interface import implements

from canonical.launchpad.interfaces.archiveauthtoken import (
    IArchiveAuthToken)


class ArchiveAuthToken(Storm):
    """See `IArchiveAuthToken`."""
    implements(IArchiveAuthToken)
    __storm_table__ = 'ArchiveAuthToken'

    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    person_id = Int(name='person', allow_none=False)
    person = Reference(person_id, 'Person.id')

    date_created = DateTime(
        name='date_created', allow_none=False, tzinfo=pytz.timezone('UTC'))

    date_deactivated = DateTime(
        name='date_deactivated', allow_none=True, tzinfo=pytz.timezone('UTC'))

    token = RawStr(name='token', allow_none=False)

