# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for package queue."""

__metaclass__ = type

__all__ = [
    'QueueItemsView',
    ]
from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    IHasQueueItems, IPackageUploadSet, QueueInconsistentStateError,
    UnexpectedFormData, ILaunchpadCelebrities, PackageUploadStatus)
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.authorization import check_permission

QUEUE_SIZE = 20


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
                'No suitable status found for value "%s"' % state_value
                )

        self.queue = self.context.getPackageUploadQueue(self.state)

        if not check_permission('launchpad.View', self.queue):
            raise Unauthorized("User don't have permission to see this queue.")

        valid_states = [
            PackageUploadStatus.NEW,
            PackageUploadStatus.ACCEPTED,
            PackageUploadStatus.REJECTED,
            PackageUploadStatus.DONE,
            PackageUploadStatus.UNAPPROVED,
            ]

        if not check_permission('launchpad.Edit', self.queue):
            # Omit the UNAPPROVED status, which the user is unable to
            # view anyway. If he hand-hacks the URL, all he will get is
            # a Forbidden which is enforced by the security wrapper for
            # Upload.
            valid_states.remove(PackageUploadStatus.UNAPPROVED)

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
        if self.request.method != "POST":
            return

        if not check_permission('launchpad.Edit', self.queue):
            self.error = 'You do not have permission to act on queue items.'
            return

        accept = self.request.form.get('Accept', '')
        reject = self.request.form.get('Reject', '')
        queue_ids = self.request.form.get('QUEUE_ID', '')

        if (not accept and not reject) or not queue_ids:
            return

        if not isinstance(queue_ids, list):
            queue_ids = [queue_ids]

        queue_set = getUtility(IPackageUploadSet)

        if accept:
            header = 'Accepting Results:<br>'
            def queue_action(queue_item):
                queue_item.setAccepted()
        elif reject:
            header = 'Rejecting Results:<br>'
            def queue_action(queue_item):
                queue_item.setRejected()

        success = []
        failure = []
        for queue_id in queue_ids:
            queue_item = queue_set.get(int(queue_id))
            try:
                queue_action(queue_item)
            except QueueInconsistentStateError, info:
                failure.append('FAILED: %s (%s)' %
                               (queue_item.displayname, info))
            else:
                success.append('OK: %s' % queue_item.displayname)

            queue_item.syncUpdate()

        report = '%s<br>%s' % (header, ', '.join(success + failure))
        return report

