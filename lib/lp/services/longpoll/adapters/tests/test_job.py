# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getMultiAdapter

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.longpoll.interfaces import ILongPollEvent
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.testing import TestCase


class TestJobLongPollEvent(TestCase):

    layer = DatabaseFunctionalLayer

    def test_adapt(self):
        job = Job()
        adapter = getMultiAdapter(
            (job, JobStatus.RUNNING), ILongPollEvent)
        self.assertEqual(
            "longpoll.event.job.%d.RUNNING" % job.id,
            adapter.event_key)
