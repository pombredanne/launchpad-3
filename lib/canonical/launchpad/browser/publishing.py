# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for publising."""

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

    def isSuperseded(self):
        return self.context.supersededby is not None

    def isPendingRemoval(self):
        return self.context.scheduleddeletiondate is not None

    def isRemoved(self):
        return self.context.dateremoved is not None

    def wasDeleted(self):
        return self.context.status == PackagePublishingStatus.DELETED


class SourcePublishingRecordView(BasePublishingRecordView):
    """View class for `ISourcePackagePublishingHistory`."""
    __used_for__ = ISourcePackagePublishingHistory


class BinaryPublishingRecordView(BasePublishingRecordView):
    """View class for `IBinaryPackagePublishingHistory`."""
    __used_for__ = IBinaryPackagePublishingHistory
