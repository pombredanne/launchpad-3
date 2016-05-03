# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for communication with the snap store."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BadRequestPackageUploadResponse',
    'BadUploadResponse',
    'ISnapStoreClient',
    ]

from zope.interface import Interface


class BadRequestPackageUploadResponse(Exception):
    pass


class BadUploadResponse(Exception):
    pass


class ISnapStoreClient(Interface):
    """Interface for the API provided by the snap store."""

    def requestPackageUpload(snap_series, snap_name):
        """Request permission from the store to upload builds of a snap.

        :param snap_series: The `ISnapSeries` in which this snap should be
            published on the store.
        :param snap_name: The registered name of this snap on the store.
        :return: A serialized macaroon appropriate for uploading builds of
            this snap.
        """

    def upload(snapbuild):
        """Upload a snap build to the store.

        :param snapbuild: The `ISnapBuild` to upload.
        """
