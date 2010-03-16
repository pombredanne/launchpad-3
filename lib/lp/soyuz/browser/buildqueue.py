# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View class for `IBuildQueue`."""

__metaclass__ = type
__all__ = [
    'BuildQueueStatusView'
    ]

from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.publisher import LaunchpadView

from lp.soyuz.interfaces.buildpackagejob import IBuildPackageJob


class BuildQueueStatusView(LaunchpadView):
    """View for `BuildQueue` status and log."""
    @property
    def log_visible(self):
        """Is the current user allowed to see the log?"""
        if IBuildPackageJob.providedBy(self.context.specific_job):
            # This job type has some kind of BuildBase associated with
            # it.  Check its view permissions.  This may not seem to
            # make much sense but countless generations before us have
            # done it this way.
            return check_permission(
                'launchpad.View', self.context.specific_job.build)
        else:
            return check_permission('launchpad.View', self.context)
