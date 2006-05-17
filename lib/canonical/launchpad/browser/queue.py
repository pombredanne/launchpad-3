# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for package queue."""

__metaclass__ = type

__all__ = [
    'QueueItemsView',
    ]
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (
    IHasQueueItems, IDistroReleaseQueueSet, QueueInconsistentStateError)
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.lp.dbschema import DistroReleaseQueueStatus

from canonical.launchpad.helpers import check_permission

QUEUE_SIZE = 20


class QueueItemsView(LaunchpadView):
    """Base class used to present objects that contain queue items.

    It retrieves the UI queue_state selector action and sets up a proper
    batched list with the requested results. See further UI details in
    template/distrorelease-queue.pt and callsite details in DistroRelease
    view classes.
    """
    __used_for__ = IHasQueueItems

    def setupQueueList(self):
        """Setup a batched queue list.

        Returns None, so use tal:condition="not: view/setupQueueList" to
        invoke it in template.
        """

        # recover selected queue state and name filter
        self.state_txt = self.request.get('queue_state', '')
        self.name_filter = self.request.get('queue_text', '')

        # expose state for page template. the fallback is "new"
        self.show_new = False
        self.show_unapproved = False
        self.show_accepted = False
        self.show_rejected = False
        self.show_done = False

        if self.state_txt == 'unapproved':
            self.state = DistroReleaseQueueStatus.UNAPPROVED
            self.show_unapproved = True
        elif self.state_txt == 'accepted':
            self.state = DistroReleaseQueueStatus.ACCEPTED
            self.show_accepted = True
        elif self.state_txt == 'rejected':
            self.state = DistroReleaseQueueStatus.REJECTED
            self.show_rejected = True
        elif self.state_txt == 'done':
            self.state = DistroReleaseQueueStatus.DONE
            self.show_done = True
        else:
            # this is the fallback
            self.state = DistroReleaseQueueStatus.NEW
            self.show_new = True

        # enforce security again: only someone with launchpad.Admin on the
        # distrorelease should be able to see the unapproved queue
        # NB: sabdfl: this is not a rigorous way of enforcing this kind of
        # security!
        if (self.state == DistroReleaseQueueStatus.UNAPPROVED and
            not check_permission('launchpad.Admin', self.context)):
            self.error = (
                "Sorry, you do not have permission to view this queue, "
                "we have excluded any packages from this listing.")
            return

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
            DistroReleaseQueueStatus.NEW,
            DistroReleaseQueueStatus.UNAPPROVED,
            ]

        # return actions only for supported states and require
        # admin permission
        if (self.state in mutable_states and
            check_permission('launchpad.Admin', self.context)):
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

        if not check_permission('launchpad.Admin', self.context):
            self.error = 'You do not have permission to act on queue items.'
            return

        accept = self.request.form.get('Accept', '')
        reject = self.request.form.get('Reject', '')
        queue_ids = self.request.form.get('QUEUE_ID', '')

        if (not accept and not reject) or not queue_ids:
            return

        if not isinstance(queue_ids, list):
            queue_ids = [queue_ids]

        queue_set = getUtility(IDistroReleaseQueueSet)

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

        flush_database_updates()

        report = '%s<br>%s' % (header, ', '.join(success + failure))
        return report

