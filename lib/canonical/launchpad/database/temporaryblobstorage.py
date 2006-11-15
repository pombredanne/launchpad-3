# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TemporaryBlobStorage',
    'TemporaryStorageManager',
    ]

from zope.interface import implements

from sqlobject import StringCol

from datetime import timedelta

from canonical import uuid

from canonical.launchpad.interfaces import (
    ITemporaryBlobStorage,
    ITemporaryStorageManager)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol


class TemporaryBlobStorage(SQLBase):
    """A temporary BLOB stored in Launchpad."""

    implements(ITemporaryBlobStorage)

    _table='TemporaryBlobStorage'

    uuid = StringCol(notNull=True, alternateID=True)
    blob = StringCol(notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)


class TemporaryStorageManager:
    """A tool to create temporary BLOB's in Launchpad."""

    implements(ITemporaryStorageManager)

    def new(self, blob):
        """See ITemporaryStorageManager."""
        # at this stage we could do some sort of throttling if we were
        # concerned about abuse of the temporary storage facility. For
        # example, we could check the number of rows in temporary storage,
        # or the total amount of space dedicated to temporary storage, and
        # return an error code if that volume was unacceptably high. But for
        # the moment we will just ensure the BLOB is not that LARGE
        if len(blob) > 320000:
            return None
        # create the BLOB and return the UUID
        new_uuid = str(uuid.generate_uuid())
        tempblob = TemporaryBlobStorage(uuid=new_uuid, blob=blob)
        return new_uuid

    def sweep(self, age_in_seconds):
        """See ITemporaryStorageManager."""
        expiredset = TemporaryBlobStorage.select(
            """date_created < CURRENT_TIMESTAMP
               AT TIME ZONE 'UTC' - '%s seconds'::interval""" % (
                age_in_seconds))
        number_swept = expiredset.count()
        for expired_blob in expiredset:
            TemporaryBlobStorage.delete(expired_blob.id)
        return number_swept

    def fetch(self, uuid):
        """See ITemporaryStorageManager."""
        return TemporaryBlobStorage.selectOneBy(uuid=uuid)

    def delete(self, uuid):
        """See ITemporaryStorageManager."""
        blob = TemporaryBlobStorage.selectOneBy(uuid=uuid)
        if blob is not None:
            TemporaryBlobStorage.delete(blob.id)

