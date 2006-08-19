# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for TemporaryBlobStorage."""

__metaclass__ = type
__all__ = [
    'TemporaryBlobStorageAddView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import ITemporaryStorageManager

from canonical.launchpad.webapp import GeneralFormView


class TemporaryBlobStorageAddView(GeneralFormView):

    def process(self, blob):
        uuid = getUtility(ITemporaryStorageManager).new(blob)
        if not uuid:
            return 'No blob storage available.'
        return 'Your ticket is "%s"' % uuid


