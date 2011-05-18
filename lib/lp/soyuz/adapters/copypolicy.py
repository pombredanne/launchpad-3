# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Copy Policy Classes.

The classes contain various policies about copying packages that can be
decided at runtime, such as whether to auto-accept a package or not.
"""

__metaclass__ = type

__all__ = [
    "InsecureCopyPolicy",
    ]


from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus


class BaseCopyPolicy:
    """Encapsulation of the policies for copying a package in Launchpad."""

    def autoApprove(self, packageupload):
        """Decide if the packageupload can be approved automatically or
        should be held in the queue.
        """
        raise AssertionError("Subclass must provide autoApprove")

    def autoApproveNew(self, packageupload):
        """Decide if a previously unknown package is approved automatically
        or should be held in the queue.
        """
        raise AssertionError("Subclass must provide autoApproveNew")


class InsecureCopyPolicy(BaseCopyPolicy):
    """A policy for copying from insecure sources."""

    def autoApproveNew(self, packageupload):
        if packageupload.isPPA():
            return True
        return False

    def autoApprove(self, packageupload):
        if packageupload.isPPA():
            return True

        # This check is orthogonal to the
        # IDistroSeries.canUploadToPocket check.
        if (packageupload.pocket == PackagePublishingPocket.RELEASE and
            packageupload.distroseries.status != SeriesStatus.FROZEN):
            return True

        return False
