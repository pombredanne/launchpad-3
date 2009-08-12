# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Temporary blob storage interfaces."""

__metaclass__ = type

__all__ = [
    'ITemporaryBlobStorage',
    'ITemporaryStorageManager',
    'BlobTooLarge',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Datetime, Text, Bytes
from canonical.launchpad import _

class BlobTooLarge(Exception):
    """Raised if attempting to create a blob larger than the maximum
       allowed size.
    """
    pass


class ITemporaryBlobStorage(Interface):
    """A blob which we will store in the database temporarily."""

    uuid = Text(title=_('UUID'), required=True, readonly=True)
    blob = Bytes(title=_('BLOB'), required=True, readonly=True)
    date_created = Datetime(title=_('Date created'),
        required=True, readonly=True)
    file_alias = Attribute("Link to actual storage of blob")


class ITemporaryStorageManager(Interface):
    """A tool to create temporary blobs."""

    def new(blob, expires=None):
        """Create a new blob for storage in the database, returning the
        UUID assigned to it.

        May raise a BlobTooLarge exception.

        Default expiry timestamp is calculated using
        config.launchpad.default_blob_expiry
        """

    def fetch(uuid):
        """Retrieve a TemporaryBlobStorage by uuid."""

    def delete(uuid):
        """Delete a TemporaryBlobStorage by uuid."""

