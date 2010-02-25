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

from lazr.restful.fields import Reference
from lazr.restful.declarations import (
    call_with, collection_default_content, exported,
    export_as_webservice_collection, export_as_webservice_entry,
    export_read_operation, operation_parameters, REQUEST_USER)
from lazr.restful.interface import copy_field


class BlobTooLarge(Exception):
    """Raised if attempting to create a blob larger than the maximum
       allowed size.
    """
    pass


class ITemporaryBlobStorage(Interface):
    """A blob which we will store in the database temporarily."""
    export_as_webservice_entry(
        singular_name='temporary_blob', plural_name='temporary_blobs')

    uuid = exported(
        Text(title=_('UUID'), required=True, readonly=True),
        exported_as='token')
    blob = Bytes(title=_('BLOB'), required=True, readonly=True)
    date_created = Datetime(title=_('Date created'),
        required=True, readonly=True)
    file_alias = Attribute("Link to actual storage of blob")
    has_been_processed = Attribute("Whether the blob has been processed.")


class ITemporaryStorageManager(Interface):
    """A tool to create temporary blobs."""
    export_as_webservice_collection(ITemporaryBlobStorage)

    def new(blob, expires=None):
        """Create a new blob for storage in the database, returning the
        UUID assigned to it.

        May raise a BlobTooLarge exception.

        Default expiry timestamp is calculated using
        config.launchpad.default_blob_expiry
        """

    @operation_parameters(uuid=copy_field(ITemporaryBlobStorage['uuid']))
    @export_read_operation()
    def fetch(uuid):
        """Retrieve a TemporaryBlobStorage by uuid."""

    def delete(uuid):
        """Delete a TemporaryBlobStorage by uuid."""

    @collection_default_content(user=REQUEST_USER)
    def default_temporary_blob_storage_list(user):
        """Return the default list of ITemporaryBlobStorage objects."""
