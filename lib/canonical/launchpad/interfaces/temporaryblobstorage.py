# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Temporary blob storage interfaces."""

__metaclass__ = type

__all__ = [
    'ITemporaryBlobStorage',
    'ITemporaryStorageManager',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Text
from canonical.launchpad import _

class ITemporaryBlobStorage(Interface):
    """A blob which we will store in the database temporarily."""

    uuid = Text(title=_('UUID'), required=True, readonly=True)
    blob = Text(title=_('BLOB'), required=True, readonly=True)
    date_created = Datetime(title=_('Date created'),
        required=True, readonly=True)


class ITemporaryStorageManager(Interface):
    """A tool to create temporary blobs."""
    
    def new(blob):
        """Create a new blob for storage in the database, returning the
        UUID assigned to it."""

    def sweep(age_in_seconds):
        """Clean up all the expired BLOB's. Age is the allowed age of a
        BLOB, in seconds, during this sweep."""

    def fetch(uuid):
        """Retrieve a TemporaryBlobStorage by uuid."""

    def delete(uuid):
        """Delete a TemporaryBlobStorage by uuid."""

