# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
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
from lp.services.job.interfaces.job import JobStatus
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
    structured,
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

    @cachedproperty
    def store_upload_status(self):
        job = self.context.store_upload_jobs.first()
        if job is None:
            return None
        elif job.job.status in (JobStatus.WAITING, JobStatus.RUNNING):
            return "Store upload in progress"
        elif job.job.status == JobStatus.COMPLETED:
            return structured(
                '<a href="%s">Manage this package in the store</a>',
                job.store_url)
        elif job.store_url:
            return structured(
                '<a href="%s">Manage this package in the store</a><br />'
                'Releasing package to channels failed: %s',
                job.store_url, job.error_message)
        else:
            return structured("Store upload failed: %s", job.error_message)


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
