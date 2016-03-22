# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SnapBuild views."""

__metaclass__ = type
__all__ = [
    'SnapBuildContextMenu',
    'SnapBuildNavigation',
    'SnapBuildView',
    ]

from zope.interface import Interface

from lp.app.browser.launchpadform import (
    action,
    LaunchpadFormView,
    )
from lp.buildmaster.enums import BuildQueueStatus
from lp.services.librarian.browser import (
    FileNavigationMixin,
    ProxiedLibraryFileAlias,
    )
from lp.services.propertycache import cachedproperty
from lp.services.webapp import (
    canonical_url,
    ContextMenu,
    enabled_with_permission,
    LaunchpadView,
    Link,
    Navigation,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.soyuz.interfaces.binarypackagebuild import IBuildRescoreForm


class SnapBuildNavigation(Navigation, FileNavigationMixin):
    usedfor = ISnapBuild


class SnapBuildContextMenu(ContextMenu):
    """Context menu for snap package builds."""

    usedfor = ISnapBuild

    facet = 'overview'

    links = ('cancel', 'rescore')

    @enabled_with_permission('launchpad.Edit')
    def cancel(self):
        return Link(
            '+cancel', 'Cancel build', icon='remove',
            enabled=self.context.can_be_cancelled)

    @enabled_with_permission('launchpad.Admin')
    def rescore(self):
        return Link(
            '+rescore', 'Rescore build', icon='edit',
            enabled=self.context.can_be_rescored)


class SnapBuildView(LaunchpadView):
    """Default view of a SnapBuild."""

    @property
    def label(self):
        return self.context.title

    page_title = label

    @cachedproperty
    def eta(self):
        """The datetime when the build job is estimated to complete.

        This is the BuildQueue.estimated_duration plus the
        Job.date_started or BuildQueue.getEstimatedJobStartTime.
        """
        if self.context.buildqueue_record is None:
            return None
        queue_record = self.context.buildqueue_record
        if queue_record.status == BuildQueueStatus.WAITING:
            start_time = queue_record.getEstimatedJobStartTime()
        else:
            start_time = queue_record.date_started
        if start_time is None:
            return None
        duration = queue_record.estimated_duration
        return start_time + duration

    @cachedproperty
    def estimate(self):
        """If true, the date value is an estimate."""
        if self.context.date_finished is not None:
            return False
        return self.eta is not None

    @cachedproperty
    def date(self):
        """The date when the build completed or is estimated to complete."""
        if self.estimate:
            return self.eta
        return self.context.date_finished

    @cachedproperty
    def files(self):
        """Return `LibraryFileAlias`es for files produced by this build."""
        if not self.context.was_built:
            return None

        return [
            ProxiedLibraryFileAlias(alias, self.context)
            for _, alias, _ in self.context.getFiles() if not alias.deleted]

    @cachedproperty
    def has_files(self):
        return bool(self.files)


class SnapBuildCancelView(LaunchpadFormView):
    """View for cancelling a snap package build."""

    class schema(Interface):
        """Schema for cancelling a build."""

    page_title = label = 'Cancel build'

    @property
    def cancel_url(self):
        return canonical_url(self.context)
    next_url = cancel_url

    @action('Cancel build', name='cancel')
    def request_action(self, action, data):
        """Cancel the build."""
        self.context.cancel()


class SnapBuildRescoreView(LaunchpadFormView):
    """View for rescoring a snap package build."""

    schema = IBuildRescoreForm

    page_title = label = 'Rescore build'

    def __call__(self):
        if self.context.can_be_rescored:
            return super(SnapBuildRescoreView, self).__call__()
        self.request.response.addWarningNotification(
            "Cannot rescore this build because it is not queued.")
        self.request.response.redirect(canonical_url(self.context))

    @property
    def cancel_url(self):
        return canonical_url(self.context)
    next_url = cancel_url

    @action('Rescore build', name='rescore')
    def request_action(self, action, data):
        """Rescore the build."""
        score = data.get('priority')
        self.context.rescore(score)
        self.request.response.addNotification('Build rescored to %s.' % score)

    @property
    def initial_values(self):
        return {'score': str(self.context.buildqueue_record.lastscore)}
