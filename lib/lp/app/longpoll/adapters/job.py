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

from lp.app.longpoll.adapters.emitter import LongPollEmitter
from lp.app.longpoll.interfaces import ILongPollEvent
from lp.services.job.interfaces.job import (
    IJob,
    JobStatus,
    )


class JobLongPollEmitter(LongPollEmitter):

    adapts(IJob, Interface)
    implements(ILongPollEvent)

    def __init__(self, source, event):
        if event not in JobStatus:
            raise AssertionError(
                "%r does not emit %r events." % (source, event))
        super(JobLongPollEmitter, self).__init__(source, event)

    @property
    def event_key(self):
        return "longpoll.job.%d.%s" % (
            self.source.job_id, self.event.name)
