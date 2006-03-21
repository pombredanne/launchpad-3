# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for package queue."""

__metaclass__ = type

__all__ = [
    'QueueItemsView',
    ]
from zope.component import getUtility
from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad.webapp import LaunchpadView

from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.lp.dbschema import DistroReleaseQueueStatus

from canonical.launchpad.interfaces import (
    IHasQueueItems, IDistroReleaseQueueSet, QueueInconsistentStateError)

QUEUE_SIZE = 20

class QueueItemsView(LaunchpadView):
    """Base class used to present objects that contains queue items.

    It retrieves the UI queue_state selector action and setup a proper
    batched list with the requested results. See further UI details in
    template/queue-items.pt and callsite details in DistroRelease
    view classes.
    """
    __used_for__ = IHasQueueItems

    def setupQueueList(self):
        """Setup a batched queue list.

        Return None, so use tal:condition="not: view/setupQueueList" to
        invoke it in template.
        """
        # recover selected queue state and name
        self.state = self.request.get('queue_state', '')
        self.text = self.request.get('queue_text', '')

        # map state text tag back to dbschema
        state_map = {
            '': DistroReleaseQueueStatus.NEW,
            'new': DistroReleaseQueueStatus.NEW,
            'unapproved': DistroReleaseQueueStatus.UNAPPROVED,
            'accepted': DistroReleaseQueueStatus.ACCEPTED,
            'rejected': DistroReleaseQueueStatus.REJECTED,
            'done': DistroReleaseQueueStatus.DONE,
            }

        # request context queue items according the selected state
        queue_items = self.context.getQueueItems(
            status=state_map[self.state], name=self.text)
        self.batchnav = BatchNavigator(queue_items, self.request,
                                       size=QUEUE_SIZE)

    def availableActions(self):
        """Return the avaiables action according selected queue state.

        Return a list of labeled actions or an empty list.
        """
        if self.state in ['', 'new', 'unapproved']:
            return ['accept', 'reject']
        return []

    def performQueueAction(self):
        """Execute the designed action over the selected queue items.

        Return a message describing the action executed or None if nothing
        was done.
        """
        if self.request.method != "POST":
            return

        action = self.request.form.get('queue_action', '')
        queue_ids = self.request.form.get('QUEUE_ID', '')

        if not action or not queue_ids:
            return

        if not isinstance(queue_ids, list):
            queue_ids = [queue_ids]

        queue_set = getUtility(IDistroReleaseQueueSet)

        action_map = {
            'accept': 'setAccepted',
            'reject': 'setRejected',
            }

        success = []
        failure = []
        for queue_id in queue_ids:
            queue = queue_set.get(int(queue_id))
            try:
                getattr(queue, action_map[action])()
            except QueueInconsistentStateError, info:
                failure.append('FAILED: %s (%s)' %(queue.displayname, info))
            else:
                success.append('OK: %s' % queue.displayname)

        flush_database_updates()

        report = '%s result<br>%s'% (action.upper(),
                                     '<br>'.join(success + failure))
        return report
