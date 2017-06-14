# Copyright 2016-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for communication with the snap store."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BadRefreshResponse',
    'BadRequestPackageUploadResponse',
    'BadScanStatusResponse',
    'BadSearchResponse',
    'ISnapStoreClient',
    'NeedsRefreshResponse',
    'ReleaseFailedResponse',
    'ScanFailedResponse',
    'SnapStoreError',
    'UnauthorizedUploadResponse',
    'UploadFailedResponse',
    'UploadNotScannedYetResponse',
    ]

import httplib

from lazr.restful.declarations import error_status
from zope.interface import Interface


class SnapStoreError(Exception):

    def __init__(self, message="", detail=None):
        super(SnapStoreError, self).__init__(message)
        self.message = message
        self.detail = detail


@error_status(httplib.INTERNAL_SERVER_ERROR)
class BadRequestPackageUploadResponse(SnapStoreError):
    pass


class UploadFailedResponse(SnapStoreError):
    pass


class BadRefreshResponse(SnapStoreError):
    pass


class NeedsRefreshResponse(SnapStoreError):
    pass


class UnauthorizedUploadResponse(SnapStoreError):
    pass


class BadScanStatusResponse(SnapStoreError):
    pass


class UploadNotScannedYetResponse(SnapStoreError):
    pass


class ScanFailedResponse(SnapStoreError):
    pass


class BadSearchResponse(SnapStoreError):
    pass


class ReleaseFailedResponse(SnapStoreError):
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
        :return: A URL to poll for upload processing status.
        :raises BadRefreshResponse: if the authorising macaroons need to be
            refreshed, but attempting to do so fails.
        :raises UnauthorizedUploadResponse: if the user who authorised this
            upload is not themselves authorised to upload the snap in
            question.
        :raises UploadFailedResponse: if uploading the build to the store
            failed.
        """

    def refreshDischargeMacaroon(snap):
        """Refresh a snap's discharge macaroon.

        :param snap: An `ISnap` whose discharge macaroon needs to be refreshed.
        """

    def checkStatus(status_url):
        """Poll the store once for upload scan status.

        :param status_url: A URL as returned by `upload`.
        :raises UploadNotScannedYetResponse: if the store has not yet
            scanned the upload.
        :raises BadScanStatusResponse: if the store failed to scan the
            upload.
        :return: A tuple of (`url`, `revision`), where `url` is a URL on the
            store with further information about this upload, and `revision`
            is the store revision number for the upload or None.
        """

    def listChannels():
        """Fetch the current list of channels from the store.

        :raises BadSearchResponse: if the attempt to fetch the list of
            channels from the store fails.
        :return: A list of dictionaries, one per channel, each of which
            contains at least "name" and "display_name" keys.
        """

    def release(snapbuild, revision):
        """Tell the store to release a snap build to specified channels.

        :param snapbuild: The `ISnapBuild` to release.
        :param revision: The revision returned by the store when uploading
            the build.
        :raises ReleaseFailedResponse: if the store failed to release the
            build.
        """
