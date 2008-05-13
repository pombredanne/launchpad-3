# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for package queue."""

__metaclass__ = type

__all__ = [
    'QueueItemsView',
    ]

import operator

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IArchivePermissionSet, IComponentSet, IHasQueueItems, IPackageUploadSet,
    ISectionSet, NotFoundError, PackagePublishingPriority,
    QueueInconsistentStateError, UnexpectedFormData, PackageUploadStatus)
from canonical.launchpad.scripts.queue import name_priority_map
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.authorization import check_permission

QUEUE_SIZE = 30


class QueueItemsView(LaunchpadView):
    """Base class used to present objects that contain queue items.

    It retrieves the UI queue_state selector action and sets up a proper
    batched list with the requested results. See further UI details in
    template/distroseries-queue.pt and callsite details in DistroSeries
    view classes.
    """
    __used_for__ = IHasQueueItems

    def setupQueueList(self):
        """Setup a batched queue list.

        Returns None, so use tal:condition="not: view/setupQueueList" to
        invoke it in template.
        """

        # recover selected queue state and name filter
        self.name_filter = self.request.get('queue_text', '')

        try:
            state_value = int(self.request.get('queue_state', ''))
        except ValueError:
            state_value = 0

        try:
            self.state = PackageUploadStatus.items[state_value]
        except KeyError:
            raise UnexpectedFormData(
                'No suitable status found for value "%s"' % state_value)

        self.queue = self.context.getPackageUploadQueue(self.state)

        valid_states = [
            PackageUploadStatus.NEW,
            PackageUploadStatus.ACCEPTED,
            PackageUploadStatus.REJECTED,
            PackageUploadStatus.DONE,
            PackageUploadStatus.UNAPPROVED,
            ]

        self.filtered_options = []

        for state in valid_states:
            if state == self.state:
                selected = True
            else:
                selected = False
            self.filtered_options.append(
                dict(name=state.title, value=state.value, selected=selected)
                )

        # request context queue items according the selected state
        queue_items = self.context.getQueueItems(
            status=self.state, name=self.name_filter)
        self.batchnav = BatchNavigator(queue_items, self.request,
                                       size=QUEUE_SIZE)

    def availableActions(self):
        """Return the available actions according to the selected queue state.

        Returns a list of labelled actions or an empty list.
        """
        # states that support actions
        mutable_states = [
            PackageUploadStatus.NEW,
            PackageUploadStatus.UNAPPROVED,
            ]

        # return actions only for supported states and require
        # edit permission
        if (self.state in mutable_states and
            check_permission('launchpad.Edit', self.queue)):
            return ['Accept', 'Reject']

        # no actions for unsupported states
        return []

    def performQueueAction(self):
        """Execute the designed action over the selected queue items.

        Returns a message describing the action executed or None if nothing
        was done.
        """
        # Immediately bail out if the page is not the result of a submission.
        if self.request.method != "POST":
            return

        # Also bail out if an unauthorised user is faking submissions.
        if not check_permission('launchpad.Edit', self.queue):
            self.error = 'You do not have permission to act on queue items.'
            return

        # Retrieve the form data.
        accept = self.request.form.get('Accept', '')
        reject = self.request.form.get('Reject', '')
        component_override = self.request.form.get('component_override', '')
        section_override = self.request.form.get('section_override', '')
        priority_override = self.request.form.get('priority_override', '')
        queue_ids = self.request.form.get('QUEUE_ID', '')

        # If no boxes were checked, bail out.
        if (not accept and not reject) or not queue_ids:
            return

        # Determine if there is a source override requested.
        new_component = None
        new_section = None
        try:
            if component_override:
                new_component = getUtility(IComponentSet)[component_override]
        except NotFoundError:
            self.error = "Invalid component: %s" % component_override
            return

        # Get a list of components that the user has righs to accept and
        # override to or from.
        permission_set = getUtility(IArchivePermissionSet)
        permissions = permission_set.componentsForQueueAdmin(
            self.context.main_archive, self.user)
        allowed_components = set(
            permission.component for permission in permissions)

        try:
            if section_override:
                new_section = getUtility(ISectionSet)[section_override]
        except NotFoundError:
            self.error = "Invalid section: %s" % section_override
            return

        # Determine if there is a binary override requested.
        new_priority = None
        if priority_override not in name_priority_map:
            self.error = "Invalid priority: %s" % priority_override
            return

        new_priority = name_priority_map[priority_override]

        # Process the requested action.
        if not isinstance(queue_ids, list):
            queue_ids = [queue_ids]

        queue_set = getUtility(IPackageUploadSet)

        if accept:
            header = 'Accepting Results:<br>'
            action = "accept"
        elif reject:
            header = 'Rejecting Results:<br>'
            action = "reject"

        success = []
        failure = []
        for queue_id in queue_ids:
            queue_item = queue_set.get(int(queue_id))
            # First check that the user has rights to accept/reject this
            # item by virtue of which component it has.
            existing_components = set()
            if queue_item.contains_source:
                existing_components.add(
                    queue_item.sourcepackagerelease.component)
            else:
                # For builds we need to iterate through all its binaries
                # and collect each component.
                for build in queue_item.builds:
                    for binary in build.build.binarypackages:
                        existing_components.add(binary.component)

            existing_component_names = ", ".join(
                component.name for component in existing_components)

            # The intersection of allowed_components and
            # existing_components must be equal to existing_components
            # to allow the operation to go ahead.
            if (allowed_components.intersection(existing_components)
                != existing_components):
                failure.append("FAILED: %s (You have no rights to accept component(s) '%s')"
                    % (queue_item.displayname, existing_component_names))
                continue

            # Sources and binaries are mutually exclusive when it comes to
            # overriding, so only one of these will be set.
            try:
                source_overridden = queue_item.overrideSource(
                    new_component, new_section, allowed_components)
                binary_overridden = queue_item.overrideBinaries(
                    new_component, new_section, new_priority,
                    allowed_components)
            except QueueInconsistentStateError, info:
                failure.append("FAILED: %s (%s)" %
                               (queue_item.displayname, info))
                continue

            feedback_interpolations = {
                "name"      : queue_item.displayname,
                "component" : "(unchanged)",
                "section"   : "(unchanged)",
                "priority"  : "(unchanged)",
                }
            if new_component:
                feedback_interpolations['component'] = new_component.name
            if new_section:
                feedback_interpolations['section'] = new_section.name
            if new_priority:
                feedback_interpolations[
                    'priority'] = new_priority.title.lower()

            try:
                getattr(self, 'queue_action_' + action)(queue_item)
            except QueueInconsistentStateError, info:
                failure.append('FAILED: %s (%s)' %
                               (queue_item.displayname, info))
            else:
                if source_overridden:
                    success.append("OK: %(name)s(%(component)s/%(section)s)" %
                                   feedback_interpolations)
                elif binary_overridden:
                    success.append(
                        "OK: %(name)s(%(component)s/%(section)s/%(priority)s)"
                            % feedback_interpolations)
                else:
                    success.append('OK: %s' % queue_item.displayname)

        report = '%s<br>%s' % (header, ', '.join(success + failure))
        return report

    def queue_action_accept(self, queue_item):
        """Reject the queue item passed."""
        queue_item.acceptFromQueue(announce_list=self.context.changeslist)

    def queue_action_reject(self, queue_item):
        """Accept the queue item passed."""
        queue_item.rejectFromQueue()

    def sortedSections(self):
        """Possible sections for the context distroseries.

        Return an iterable of possible sections for the context distroseries
        sorted by their name.
        """
        return sorted(
            self.context.sections, key=operator.attrgetter('name'))

    def priorities(self):
        """An iterable of priorities from PackagePublishingPriority."""
        return (priority for priority in PackagePublishingPriority)
