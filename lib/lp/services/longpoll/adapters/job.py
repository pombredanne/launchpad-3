# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long poll event adapters."""

__metaclass__ = type
__all__ = []


from zope.component import adapts
from zope.interface import (
    implements,
    Interface,
    )

from lp.services.longpoll.adapters.event import (
    generate_event_key,
    LongPollEvent,
    )
from lp.services.longpoll.interfaces import ILongPollEvent
from lp.services.job.interfaces.job import (
    IJob,
    JobStatus,
    )


class JobLongPollEvent(LongPollEvent):

    adapts(IJob, Interface)
    implements(ILongPollEvent)

    def __init__(self, source, event):
        if event not in JobStatus:
            raise AssertionError(
                "%r does not emit %r events." % (source, event))
        super(JobLongPollEvent, self).__init__(source, event)

    @property
    def event_key(self):
        return generate_event_key(
            "job", self.source.job_id, self.event.name)
