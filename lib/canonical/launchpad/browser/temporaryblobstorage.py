# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Views for TemporaryBlobStorage."""

__metaclass__ = type
__all__ = [
    'TemporaryBlobStorageAddView',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.launchpadform import action, LaunchpadFormView

from canonical.launchpad.interfaces.temporaryblobstorage import (
    BlobTooLarge, ITemporaryBlobStorage, ITemporaryStorageManager)
from canonical.librarian.interfaces import UploadFailed


class TemporaryBlobStorageAddView(LaunchpadFormView):
    schema = ITemporaryBlobStorage
    label = 'Store BLOB'
    field_names = ['blob']
    for_input = True

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        try:
            uuid = getUtility(ITemporaryStorageManager).new(data['blob'])
            self.request.response.setHeader('X-Launchpad-Blob-Token', uuid)
            self.request.response.addInfoNotification(
                'Your ticket is "%s"' % uuid)
        except BlobTooLarge:
            self.addError('Uploaded file was too large.')
        except UploadFailed:
            self.addError('File storage unavailable - try again later.')

