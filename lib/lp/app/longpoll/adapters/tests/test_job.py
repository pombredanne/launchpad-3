# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCase
from lp.app.longpoll.interfaces import ILongPollEvent
from zope.component import getMultiAdapter


class TestJobLongPollEmitter(TestCase):

    layer = DatabaseFunctionalLayer

    def test_adapt(self):
        job = Job()
        adapter = getMultiAdapter(
            (job, JobStatus.RUNNING), ILongPollEvent)
        self.assertEqual(
            "longpoll.job.%d.RUNNING" % job.id,
            adapter.event_key)
