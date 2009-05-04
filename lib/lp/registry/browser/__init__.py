# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'RegistryDeleteViewMixin',
    ]


from zope.component import getUtility
from canonical.launchpad.interfaces.bugtask import (
    BugTaskSearchParams, IBugTaskSet)
from canonical.launchpad.webapp import canonical_url


class RegistryDeleteViewMixin:
    """A mixin class that provides common behaviour for registry deletions."""

    @property
    def cancel_url(self):
        """The context's URL."""
        return canonical_url(self.context)

    def _getBugtasks(self, milestone):
        """Return the list `IBugTask`s targeted to the milestone."""
        params = BugTaskSearchParams(milestone=milestone, user=None)
        bugtasks = getUtility(IBugTaskSet).search(params)
        return list(bugtasks)

    def _getSpecifications(self, milestone):
        """Return the list `ISpecification`s targeted to the milestone."""
        return list(milestone.specifications)

    def _getProductRelease(self, milestone):
        """The `IProductRelease` associated with the milestone."""
        return milestone.product_release

    def _getProductReleaseFiles(self, milestone):
        """The list of `IProductReleaseFile`s related to the milestone."""
        product_release = self._getProductRelease(milestone)
        if product_release is not None:
            return list(product_release.files)
        else:
            return []

    def _deleteMilestone(self, milestone):
        """Delete a milestone and unlink releated objects."""
        for bugtask in self._getBugtasks(milestone):
            bugtask.milestone = None
        for spec in self._getSpecifications(milestone):
            spec.milestone = None
        self._deleteRelease(milestone.product_release)
        milestone.destroySelf()

    def _deleteRelease(self, release):
        """Delete a release and it's files."""
        if release is not None:
            for release_file in release.files:
                release_file.destroySelf()
            release.destroySelf()
