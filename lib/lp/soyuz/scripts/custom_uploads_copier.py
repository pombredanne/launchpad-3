# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Copy latest custom uploads into a distribution release series.

Use this when initializing the installer and dist upgrader for a new release
series based on the latest uploads from its preceding series.
"""

__metaclass__ = type
__all__ = [
    'CustomUploadsCopier',
    ]

from operator import attrgetter

from zope.component import getUtility

from lp.archivepublisher.ddtp_tarball import DdtpTarballUpload
from lp.archivepublisher.debian_installer import DebianInstallerUpload
from lp.archivepublisher.dist_upgrader import DistUpgraderUpload
from lp.archivepublisher.uefi import UefiUpload
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.bulk import load_referencing
from lp.soyuz.enums import PackageUploadCustomFormat
from lp.soyuz.interfaces.archive import (
    IArchiveSet,
    MAIN_ARCHIVE_PURPOSES,
    )
from lp.soyuz.model.queue import PackageUploadCustom


class CustomUploadsCopier:
    """Copy `PackageUploadCustom` objects into a new `DistroSeries`."""

    # This is a marker as per the comment in lib/lp/soyuz/enums.py:
    ##CUSTOMFORMAT##
    # Essentially, if you alter anything to do with what custom formats are,
    # what their tags are, or anything along those lines, you should grep
    # for the marker in the source tree and fix it up in every place so
    # marked.
    copyable_types = {
        PackageUploadCustomFormat.DEBIAN_INSTALLER: DebianInstallerUpload,
        PackageUploadCustomFormat.DIST_UPGRADER: DistUpgraderUpload,
        PackageUploadCustomFormat.DDTP_TARBALL: DdtpTarballUpload,
        PackageUploadCustomFormat.UEFI: UefiUpload,
        }

    def __init__(self, target_series,
                 target_pocket=PackagePublishingPocket.RELEASE):
        self.target_series = target_series
        self.target_pocket = target_pocket

    def isCopyable(self, upload):
        """Is `upload` the kind of `PackageUploadCustom` that we can copy?"""
        return upload.customformat in self.copyable_types

    def getCandidateUploads(self, source_series,
                            source_pocket=PackagePublishingPocket.RELEASE):
        """Find custom uploads that may need copying."""
        uploads = source_series.getPackageUploads(
            pocket=source_pocket, custom_type=self.copyable_types.keys())
        load_referencing(PackageUploadCustom, uploads, ['packageuploadID'])
        customs = sum([list(upload.customfiles) for upload in uploads], [])
        customs = filter(self.isCopyable, customs)
        customs.sort(key=attrgetter('id'), reverse=True)
        return customs

    def extractSeriesKey(self, custom_type, filename):
        """Get the relevant fields out of `filename` for `custom_type`."""
        return custom_type.getSeriesKey(filename)

    def getKey(self, upload):
        """Get an indexing key for `upload`."""
        custom_format = upload.customformat
        series_key = self.extractSeriesKey(
            self.copyable_types[custom_format],
            upload.libraryfilealias.filename)
        if series_key is None:
            return None
        else:
            return (custom_format, series_key)

    def getLatestUploads(self, source_series,
                         source_pocket=PackagePublishingPocket.RELEASE):
        """Find the latest uploads.

        :param source_series: The `DistroSeries` whose uploads to get.
        :param source_pocket: The `PackagePublishingPocket` to inspect.
        :return: A dict containing the latest uploads, indexed by keys as
            returned by `getKey`.
        """
        candidate_uploads = self.getCandidateUploads(
            source_series, source_pocket=source_pocket)
        latest_uploads = {}
        for upload in candidate_uploads:
            key = self.getKey(upload)
            if key is not None:
                latest_uploads.setdefault(key, upload)
        return latest_uploads

    def getTargetArchive(self, original_archive):
        """Find counterpart of `original_archive` in `self.target_series`.

        :param original_archive: The `Archive` that the original upload went
            into.  If this is not a primary, partner, or debug archive,
            None is returned.
        :return: The `Archive` of the same purpose for `self.target_series`.
        """
        if original_archive.purpose not in MAIN_ARCHIVE_PURPOSES:
            return None
        return getUtility(IArchiveSet).getByDistroPurpose(
            self.target_series.distribution, original_archive.purpose)

    def isObsolete(self, upload, target_uploads):
        """Is `upload` superseded by one that the target series already has?

        :param upload: A `PackageUploadCustom` from the source series.
        :param target_uploads:
        """
        existing_upload = target_uploads.get(self.getKey(upload))
        return existing_upload is not None and existing_upload.id >= upload.id

    def copyUpload(self, original_upload):
        """Copy `original_upload` into `self.target_series`."""
        target_archive = self.getTargetArchive(
            original_upload.packageupload.archive)
        if target_archive is None:
            return None
        package_upload = self.target_series.createQueueEntry(
            self.target_pocket, target_archive,
            changes_file_alias=original_upload.packageupload.changesfile)
        custom = package_upload.addCustom(
            original_upload.libraryfilealias, original_upload.customformat)
        package_upload.setAccepted()
        return custom

    def copy(self, source_series,
             source_pocket=PackagePublishingPocket.RELEASE):
        """Copy uploads from `source_series`-`source_pocket`."""
        target_uploads = self.getLatestUploads(
            self.target_series, source_pocket=self.target_pocket)
        source_uploads = self.getLatestUploads(
            source_series, source_pocket=source_pocket)
        for upload in source_uploads.itervalues():
            if not self.isObsolete(upload, target_uploads):
                self.copyUpload(upload)
