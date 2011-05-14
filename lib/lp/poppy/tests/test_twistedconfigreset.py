# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for GPGHandler config reset job."""

__metaclass__ = type


from canonical.testing.layers import ZopelessLayer
from lp.poppy.twistedconfigreset import GPGHandlerConfigResetJob
from lp.testing import TestCase


class TestGPGHandlerConfigResetJob(TestCase):

    layer = ZopelessLayer

    def test_gpghandler_config_reset_job_setup(self):
        # Does the gpghandler job get setup correctly.

        job_instance = GPGHandlerConfigResetJob()
        job_instance.startService()
        self.assertIsNot(None, job_instance._gpghandler_job)
        self.assertTrue(job_instance._gpghandler_job.running)

        # It should be scheduled for every 12 hours.
        self.assertEqual(12 * 3600, job_instance._gpghandler_job.interval)

        # We should be able to stop the job.
        job_instance.stopService()
        self.assertFalse(job_instance._gpghandler_job.running)
