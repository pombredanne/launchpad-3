# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Common registry browser helpers and mixins."""

__metaclass__ = type

__all__ = [
    'get_status_count',
    'MilestoneOverlayMixin',
    'RegistryDeleteViewMixin',
    'StatusCount',
    ]


from operator import attrgetter

from zope.component import getUtility
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams, IBugTaskSet)
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp import canonical_url


class StatusCount:
    """A helper that stores the count of status for a list of items.

    Items such as `IBugTask` and `ISpecification` can be summarised by
    their status.
    """

    def __init__(self, status, count):
        """Set the status and count."""
        self.status = status
        self.count = count


def get_status_counts(workitems, status_attr):
    """Return a list StatusCounts summarising the workitem."""
    statuses = {}
    for workitem in workitems:
        status = getattr(workitem, status_attr)
        if status not in statuses:
            statuses[status] = 0
        statuses[status] += 1
    return [
        StatusCount(status, statuses[status])
        for status in sorted(statuses, key=attrgetter('sortkey'))]


class MilestoneOverlayMixin:
    """A mixin that provides the data for the milestoneoverlay script."""

    @property
    def milestone_form_uri(self):
        """URI for form displayed by the formoverlay widget."""
        return canonical_url(self.context) + '/+addmilestone/++form++'

    @property
    def series_api_uri(self):
        """The series URL for API access."""
        return canonical_url(self.context, path_only_if_possible=True)


class RegistryDeleteViewMixin:
    """A mixin class that provides common behavior for registry deletions."""

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

    def _deleteProductSeries(self, series):
        """Remove the series and delete/unlink related objects."""
        # Delete all milestones, releases, and files.
        # Any associated bugtasks and specifications are untargeted.
        for milestone in series.all_milestones:
            self._deleteMilestone(milestone)
        # Series are not deleted because some objects like translations are
        # problematic. The series is assigned to obsolete-junk. They must be
        # renamed to avoid name collision.
        date_time = series.datecreated.strftime('%Y%m%d-%H%M%S')
        series.name = '%s-%s-%s' % (
            series.product.name, series.name, date_time)
        series.product = getUtility(ILaunchpadCelebrities).obsolete_junk

    def _deleteMilestone(self, milestone):
        """Delete a milestone and unlink related objects."""
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
