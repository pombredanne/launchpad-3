# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views for package queue."""

__metaclass__ = type

__all__ = [
    'QueueItemsView',
    ]

from canonical.lp.batching import BatchNavigator
from canonical.lp.dbschema import DistroReleaseQueueStatus

from canonical.launchpad.interfaces import IHasQueueItems

from canonical.launchpad.webapp import LaunchpadView

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
        self.batchnav = BatchNavigator(queue_items, self.request)
