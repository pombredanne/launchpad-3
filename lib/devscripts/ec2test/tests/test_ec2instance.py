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
        self.return_value = return_value
        self.simulated_failure = simulated_failure

    def __call__(self, *args, **kwargs):
        """Catch a call.

        Records the fact that an invocation was made in
        `has_been_called`.

        If you passed a `simulated_failure` to the constructor, that
        object is raised.

        :return: The `return_value` you passed to the constructor.
        """
        self.call_count += 1

        if self.simulated_failure is not None:
            raise self.simulated_failure

        return self.return_value


class MockAccount:
    """Helper for setting up an `EC2Instance` without EC2."""
    acquire_private_key = Stub()
    acquire_security_group = Stub()


class MockOutput:
    """Mock stdout/stderr output from EC2 instance."""
    output = "Mock output."


class MockBotoInstance:
    """Helper for setting up an `EC2Instance` without EC2."""
    id = 0
    state = 'running'
    public_dns_name = 'mock-instance'

    update = Stub()
    stop = Stub()
    get_console_output = MockOutput


class MockReservation:
    """Helper for setting up an `EC2Instance` without EC2."""
    def __init__(self):
        self.instances = [MockBotoInstance()]


class MockImage:
    """Helper for setting up an `EC2Instance` without EC2."""
    run = Stub(return_value=MockReservation())


class MockFailure(Exception):
    """A pretend failure from the test runner."""


class TestEC2Instance(TestCase):
    """Test running of an `EC2Instance` without EC2."""

    def setUp(self):
        session_name = None
        image = MockImage()
        instance_type = 'c1.xlarge'
        demo_networks = None
        account = MockAccount()
        from_scratch = None
        user_key = None
        login = None

        self.shutdown_watcher = Stub()

        self.instance = EC2Instance(
            session_name, image, instance_type, demo_networks, account,
            from_scratch, user_key, login)

        self.instance.shutdown = self.shutdown_watcher
        self.instance._report_traceback = Stub()
        self.instance.log = Stub()

    def _runInstance(self, runnee=None, headless=False):
        """Set up and run a mock EC2 instance."""
        if runnee is None:
            runnee = Stub()

        self.instance.set_up_and_run(False, not headless, runnee)

    def test_EC2Instance_test_baseline(self):
        # The mock EC2 instances we set up have neither started nor been
        # shut down.  After running, they have started.
        # Not a very useful test, except it establishes the basic
        # assumptions for the other tests.
        runnee = Stub()

        self.assertEqual(0, runnee.call_count)
        self.assertEqual(0, self.shutdown_watcher.call_count)

        self._runInstance(runnee)

        self.assertEqual(1, runnee.call_count)

    def test_set_up_and_run_headful(self):
        # A non-headless run executes all tests in the instance, then
        # shuts down.
        self._runInstance(headless=False)

        self.assertEqual(1, self.shutdown_watcher.call_count)

    def test_set_up_and_run_headless(self):
        # An asynchronous, headless run kicks off the tests on the
        # instance but does not shut it down.
        self._runInstance(headless=True)

        self.assertEqual(0, self.shutdown_watcher.call_count)

    def test_set_up_and_run_headful_failure(self):
        # If the test runner barfs, the instance swallows the exception
        # and shuts down.
        runnee = Stub(simulated_failure=MockFailure("Headful barfage."))

        self._runInstance(runnee, headless=False)

        self.assertEqual(1, self.shutdown_watcher.call_count)

    def test_set_up_and_run_headless_failure(self):
        # If the instance's test runner fails to set up for a headless
        # run, the instance swallows the exception and shuts down.
        runnee = Stub(simulated_failure=MockFailure("Headless boom."))

        self._runInstance(runnee, headless=True)

        self.assertEqual(1, self.shutdown_watcher.call_count)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
