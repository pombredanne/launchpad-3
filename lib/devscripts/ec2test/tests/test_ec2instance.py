# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=E0702

"""Test handling of EC2 machine images."""

__metaclass__ = type

from unittest import TestCase

from lp.testing.fakemethod import FakeMethod

from devscripts.ec2test.instance import EC2Instance


class FakeAccount:
    """Helper for setting up an `EC2Instance` without EC2."""
    acquire_private_key = FakeMethod()
    acquire_security_group = FakeMethod()


class FakeOutput:
    """Pretend stdout/stderr output from EC2 instance."""
    output = "Fake output."


class FakeBotoInstance:
    """Helper for setting up an `EC2Instance` without EC2."""
    id = 0
    state = 'running'
    public_dns_name = 'fake-instance'

    update = FakeMethod()
    stop = FakeMethod()
    get_console_output = FakeOutput


class FakeReservation:
    """Helper for setting up an `EC2Instance` without EC2."""
    def __init__(self):
        self.instances = [FakeBotoInstance()]


class FakeImage:
    """Helper for setting up an `EC2Instance` without EC2."""
    run = FakeMethod(result=FakeReservation())


class FakeFailure(Exception):
    """A pretend failure from the test runner."""


class TestEC2Instance(TestCase):
    """Test running of an `EC2Instance` without EC2."""

    def _makeInstance(self):
        """Set up an `EC2Instance`, with stubbing where needed.

        `EC2Instance.shutdown` is replaced with a `FakeMethod`, so check
        its call_count to see whether it's been invoked.
        """
        session_name = None
        image = FakeImage()
        instance_type = 'c1.xlarge'
        demo_networks = None
        account = FakeAccount()
        from_scratch = None
        user_key = None
        login = None
        region = None

        instance = EC2Instance(
            session_name, image, instance_type, demo_networks, account,
            from_scratch, user_key, login,
            region)

        instance.shutdown = FakeMethod()
        instance._report_traceback = FakeMethod()
        instance.log = FakeMethod()

        return instance

    def _runInstance(self, instance, runnee=None, headless=False):
        """Set up and run an `EC2Instance` (but without EC2)."""
        if runnee is None:
            runnee = FakeMethod()

        instance.set_up_and_run(False, not headless, runnee)

    def test_EC2Instance_test_baseline(self):
        # The EC2 instances we set up have neither started nor been shut
        # down.  After running, they have started.
        # Not a very useful test, except it establishes the basic
        # assumptions for the other tests.
        instance = self._makeInstance()
        runnee = FakeMethod()

        self.assertEqual(0, runnee.call_count)
        self.assertEqual(0, instance.shutdown.call_count)

        self._runInstance(instance, runnee=runnee)

        self.assertEqual(1, runnee.call_count)

    def test_set_up_and_run_headful(self):
        # A non-headless run executes all tests in the instance, then
        # shuts down.
        instance = self._makeInstance()

        self._runInstance(instance, headless=False)

        self.assertEqual(1, instance.shutdown.call_count)

    def test_set_up_and_run_headless(self):
        # An asynchronous, headless run kicks off the tests on the
        # instance but does not shut it down.
        instance = self._makeInstance()

        self._runInstance(instance, headless=True)

        self.assertEqual(0, instance.shutdown.call_count)

    def test_set_up_and_run_headful_failure(self):
        # If the test runner barfs, the instance swallows the exception
        # and shuts down.
        instance = self._makeInstance()
        runnee = FakeMethod(failure=FakeFailure("Headful barfage."))

        self._runInstance(instance, runnee=runnee, headless=False)

        self.assertEqual(1, instance.shutdown.call_count)

    def test_set_up_and_run_headless_failure(self):
        # If the instance's test runner fails to set up for a headless
        # run, the instance swallows the exception and shuts down.
        instance = self._makeInstance()
        runnee = FakeMethod(failure=FakeFailure("Headless boom."))

        self._runInstance(instance, runnee=runnee, headless=True)

        self.assertEqual(1, instance.shutdown.call_count)
