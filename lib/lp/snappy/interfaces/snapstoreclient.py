# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for communication with the snap store."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BadRefreshResponse',
    'BadRequestPackageUploadResponse',
    'BadUploadResponse',
    'ISnapStoreClient',
    'NeedsRefreshResponse',
    ]

from zope.interface import Interface


class BadRequestPackageUploadResponse(Exception):
    pass


class BadUploadResponse(Exception):
    pass


class BadRefreshResponse(Exception):
    pass


class NeedsRefreshResponse(Exception):
    pass


class ISnapStoreClient(Interface):
    """Interface for the API provided by the snap store."""

    def requestPackageUploadPermission(snappy_series, snap_name):
        """Request permission from the store to upload builds of a snap.

        The returned macaroon will include a third-party caveat that must be
        discharged by the login service.  This method does not acquire that
        discharge; it must be acquired separately.

        :param snappy_series: The `ISnappySeries` in which this snap should
            be published on the store.
        :param snap_name: The registered name of this snap on the store.
        :return: A serialized macaroon appropriate for uploading builds of
            this snap.
        """

    def upload(snapbuild):
        """Upload a snap build to the store.

        :param snapbuild: The `ISnapBuild` to upload.
        """

    def refreshDischargeMacaroon(snap):
        """Refresh a snap's discharge macaroon.

        :param snap: An `ISnap` whose discharge macaroon needs to be refreshed.
        """
