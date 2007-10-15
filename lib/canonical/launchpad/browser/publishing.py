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
from canonical.lp.dbschema import PackagePublishingStatus

class BasePublishingRecordView(LaunchpadView):
    """Base Publishing view class."""

    def wasDeleted(self):
        """Whether or not a publishing record  deletion was requested.

        A publishing record deletion represents the explicit request from a
        archive-administrator (self.remove_by) to purge the published contents
        of this record from the archive by a arbitrary reason
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

         * OBSOLETE -> the publication has become obsolete because it's targeted
           distroseries has become obsolete (not supported by its developers).
        """
        return self.context.dateremoved is not None


class SourcePublishingRecordView(BasePublishingRecordView):
    """View class for `ISourcePackagePublishingHistory`."""
    __used_for__ = ISourcePackagePublishingHistory


class BinaryPublishingRecordView(BasePublishingRecordView):
    """View class for `IBinaryPackagePublishingHistory`."""
    __used_for__ = IBinaryPackagePublishingHistory
