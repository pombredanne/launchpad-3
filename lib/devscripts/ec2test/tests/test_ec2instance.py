# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=E0702

"""Test handling of EC2 machine images."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from devscripts.ec2test.instance import EC2Instance


class Stub:
    """Generic recipient of invocations.

    Use this to:
     - Stub methods that should do nothing.
     - Inject failures into methods.
     - Record whether a method is being called.
    """
    # XXX JeroenVermeulen 2009-11-26: This probably exists somewhere
    # already.  Or if not, maybe it should.  But with a name that won't
    # turn Stuart Bishop's IRC client into a disco simulator. 

    call_count = 0

    def __init__(self, return_value=None, simulated_failure=None):
        """Define what to do when this stub gets invoked.

        :param return_value: Something to return from the invocation.
        :parma simulated_failure: Something to raise in the invocation.
        """
        assert return_value is None or simulated_failure is None, (
            "Stub can raise an exception or return a value, but not both.")
        self.return_value = return_value
        self.simulated_failure = simulated_failure

    def __call__(self, *args, **kwargs):
        """Catch a call.

        Records the fact that an invocation was made in
        `call_count`.

        If you passed a `simulated_failure` to the constructor, that
        object is raised.

        :return: The `return_value` you passed to the constructor.
        """
        self.call_count += 1

        if self.simulated_failure is not None:
            raise self.simulated_failure

        return self.return_value


class FakeAccount:
    """Helper for setting up an `EC2Instance` without EC2."""
    acquire_private_key = Stub()
    acquire_security_group = Stub()


class FakeOutput:
    """Pretend stdout/stderr output from EC2 instance."""
    output = "Fake output."


class FakeBotoInstance:
    """Helper for setting up an `EC2Instance` without EC2."""
    id = 0
    state = 'running'
    public_dns_name = 'fake-instance'

    update = Stub()
    stop = Stub()
    get_console_output = FakeOutput


class FakeReservation:
    """Helper for setting up an `EC2Instance` without EC2."""
    def __init__(self):
        self.instances = [FakeBotoInstance()]


class FakeImage:
    """Helper for setting up an `EC2Instance` without EC2."""
    run = Stub(return_value=FakeReservation())


class FakeFailure(Exception):
    """A pretend failure from the test runner."""


class TestEC2Instance(TestCase):
    """Test running of an `EC2Instance` without EC2."""

    def _makeInstance(self):
        """Set up an `EC2Instance`, with stubbing where needed.

        `EC2Instance.shutdown` is replaced with a `Stub`, so check its
        call_count to see whether it's been invoked.
        """
        session_name = None
        image = FakeImage()
        instance_type = 'c1.xlarge'
        demo_networks = None
        account = FakeAccount()
        from_scratch = None
        user_key = None
        login = None

        instance = EC2Instance(
            session_name, image, instance_type, demo_networks, account,
            from_scratch, user_key, login)

        instance.shutdown = Stub()
        instance._report_traceback = Stub()
        instance.log = Stub()

        return instance

    def _runInstance(self, instance, runnee=None, headless=False):
        """Set up and run an `EC2Instance` (but without EC2)."""
        if runnee is None:
            runnee = Stub()

        instance.set_up_and_run(False, not headless, runnee)

    def test_EC2Instance_test_baseline(self):
        # The EC2 instances we set up have neither started nor been shut
        # down.  After running, they have started.
        # Not a very useful test, except it establishes the basic
        # assumptions for the other tests.
        instance = self._makeInstance()
        runnee = Stub()

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
        runnee = Stub(simulated_failure=FakeFailure("Headful barfage."))

        self._runInstance(instance, runnee=runnee, headless=False)

        self.assertEqual(1, instance.shutdown.call_count)

    def test_set_up_and_run_headless_failure(self):
        # If the instance's test runner fails to set up for a headless
        # run, the instance swallows the exception and shuts down.
        instance = self._makeInstance()
        runnee = Stub(simulated_failure=FakeFailure("Headless boom."))

        self._runInstance(instance, runnee=runnee, headless=True)

        self.assertEqual(1, instance.shutdown.call_count)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
