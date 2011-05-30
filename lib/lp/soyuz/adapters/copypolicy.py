# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Copy Policy Classes.

The classes contain various policies about copying packages that can be
decided at runtime, such as whether to auto-accept a package or not.
"""

__metaclass__ = type

__all__ = [
    "InsecureCopyPolicy",
    "SyncCopyPolicy",
    ]


from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus


class BaseCopyPolicy:
    """Encapsulation of the policies for copying a package in Launchpad."""

    def autoApprove(self, archive, distroseries, pocket):
        """Decide if the upload can be approved automatically or
        should be held in the queue.

        This should only be called for packages that are known not new.

        :param archive: The target `IArchive` for the upload.
        :param distroseries: The target `IDistroSeries` for the upload.
        :param pocket: The target `PackagePublishingPocket` for the upload.
        """
        raise AssertionError("Subclass must provide autoApprove")

    def autoApproveNew(self, archive, distroseries, pocket):
        """Decide if a previously unknown package is approved automatically
        or should be held in the queue.

        :param archive: The target `IArchive` for the upload.
        :param distroseries: The target `IDistroSeries` for the upload.
        :param pocket: The target `PackagePublishingPocket` for the upload.
        """
        raise AssertionError("Subclass must provide autoApproveNew")

    @property
    def send_email(self):
        """Whether or not the copy should send emails after completing."""
        raise AssertionError("Subclass must provide send_email")


class InsecureCopyPolicy(BaseCopyPolicy):
    """A policy for copying from insecure sources."""

    def autoApproveNew(self, archive, distroseries=None, pocket=None):
        if archive.is_ppa:
            return True
        return False

    def autoApprove(self, archive, distroseries, pocket):
        if archive.is_ppa:
            return True

        # If the pocket is RELEASE and we're not frozen then you can
        # upload to it.  Any other states mean the upload is unapproved.
        #
        # This check is orthogonal to the
        # IDistroSeries.canUploadToPocket check.
        if (pocket == PackagePublishingPocket.RELEASE and
            distroseries.status != SeriesStatus.FROZEN):
            return True

        return False

    @property
    def send_email(self):
        return True


class SyncCopyPolicy(InsecureCopyPolicy):
    """A policy for mass 'sync' copies."""

    @property
    def send_email(self):
        return False
