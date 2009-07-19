# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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

    def initialize(self):
        # Need this hack here to ensure Action.__get__ doesn't add the view's
        # prefix to the action's __name__.  See note below to understand why
        # we need the action's name to be FORM_SUBMIT.
        self.actions = [action for action in self.actions]
        self.actions[0].__name__ = 'FORM_SUBMIT'
        super(TemporaryBlobStorageAddView, self).initialize()

    # NOTE: This action is named FORM_SUBMIT because apport depends on it
    # being named like that.
    @action('Continue', name='FORM_SUBMIT')
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

