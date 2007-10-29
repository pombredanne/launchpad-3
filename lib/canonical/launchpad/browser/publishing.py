# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for Soyuz publishing records."""

__metaclass__ = type

__all__ = [
    'SourcePublishingRecordView',
    'BinaryPublishingRecordView',
    ]

from canonical.launchpad.interfaces import (
    ISourcePackagePublishingHistory, IBinaryPackagePublishingHistory)
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.interfaces import PackagePublishingStatus


class BasePublishingRecordView(LaunchpadView):
    """Base Publishing view class."""

    def wasDeleted(self):
        """Whether or not a publishing record deletion was requested.

        A publishing record deletion represents the explicit request from a
        archive-administrator (self.remove_by) to purge the published contents
        of this record from the archive for an arbitrary reason
        (self.removal_comment).
        """
        return self.context.status == PackagePublishingStatus.DELETED

    def wasSuperseded(self):
        """Whether or not a publishing record was superseded.

        'Superseded' means that a new and higher version of this package was
        uploaded/built after it was published or the publishing attributes
        (section, component, priority/urgency) was modified.
        """
        return self.context.supersededby is not None

    def isPendingRemoval(self):
        """Whether or not a publishing record is marked for removal.

        This package will be removed from the archive respecting the Soyuz
        'death row' quarantine period and the absence of file references in
        the target archive.
        """
        return self.context.scheduleddeletiondate is not None

    def isRemoved(self):
        """Whether or not a publishing records was removed from the archive.

        A publishing record (all files related to it) is removed from the
        archive disk once it pass through its quarantine period and it's not
        referred by any other archive publishing record.
        Archive removal represents the act of having its content purged from
        archive disk, such situation can be triggered for different status,
        each one representing a distinct step in the Soyuz publishing workflow:

         * SUPERSEDED -> the publication is not necessary since there is already
           a newer/higher/modified version available

         * DELETED -> the publishing was explicitly marked for removal by a
           archive-administrator, it's not wanted in the archive.

         * OBSOLETE -> the publication has become obsolete because its targeted
           distroseries has become obsolete (not supported by its developers).
        """
        return self.context.dateremoved is not None


class SourcePublishingRecordView(BasePublishingRecordView):
    """View class for `ISourcePackagePublishingHistory`."""
    __used_for__ = ISourcePackagePublishingHistory

    @property
    def published_source_and_binary_files(self):
        """Return list of dicts describing all files published
           for a certain source publication.
        """
        files = list(self.context.files)
        for binary in self.context.getPublishedBinaries():
            files.extend(binary.files)
        ret = []
        urls = set()
        for f in files:
            d = {}
            url = f.libraryfilealias.http_url
            if url in urls:
                # Don't print out the same file multiple times. This
                # actually happens for arch-all builds, and is
                # particularly irritating for PPAs.
                continue
            urls.add(url)
            d["url"] = url
            d["filename"] = f.libraryfilealias.filename
            d["filesize"] = f.libraryfilealias.content.filesize
            ret.append(d)
        return ret


class BinaryPublishingRecordView(BasePublishingRecordView):
    """View class for `IBinaryPackagePublishingHistory`."""
    __used_for__ = IBinaryPackagePublishingHistory

