# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Views for TemporaryBlobStorage."""

__metaclass__ = type
__all__ = [
    'TemporaryBlobStorageAddView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import ITemporaryStorageManager
from canonical.launchpad.webapp import GeneralFormView
from canonical.launchpad.interfaces import BlobTooLarge
from canonical.librarian.interfaces import UploadFailed


class TemporaryBlobStorageAddView(GeneralFormView):

    def process(self, blob):
        try:
            uuid = getUtility(ITemporaryStorageManager).new(blob)
            self.request.response.setHeader('X-Launchpad-Blob-Token', uuid)
            return 'Your ticket is "%s"' % uuid
        except BlobTooLarge:
            return 'Uploaded file was too large.'
        except UploadFailed:
            return 'File storage unavailable - try again later.'

