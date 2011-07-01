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

from lp.app.longpoll.interfaces import ILongPollEmitter
from lp.services.job.interfaces.job import (
    IJob,
    JobStatus,
    )


class JobLongPollEmitter:

    adapts(IJob, Interface)
    implements(ILongPollEmitter)

    def __init__(self, job, status):
        self.job = job
        if status not in JobStatus:
            raise AssertionError(
                "%r does not emit %r events." % (job, status))
        self.status = status

    @property
    def emit_key(self):
        return "longpoll.job.%d.%s" % (
            self.job.id, self.status.name)
