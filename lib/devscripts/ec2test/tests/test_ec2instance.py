# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test handling of EC2 machine images."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from devscripts.ec2test.instance import EC2Instance
from devscripts.ec2test.session import EC2SessionName


class MockSessionName:
    pass


class MockAccount:
    def acquire_private_key(self):
        return None

    def acquire_security_group(self, demo_networks=None,
                               security_groups=None):
        return None


class MockOutput:
    output = "Mock output."


class MockBotoInstance:
    id = 0
    state = 'running'
    public_dns_name = 'mock-instance'

    def update(self):
        pass

    def stop(self):
        pass

    def get_console_output(self):
        return MockOutput()


class MockReservation:
    def __init__(self):
        self.instances = [MockBotoInstance()]


class MockImage:
    def run(self, key_name=None, security_groups=None, instance_type=None):
        return MockReservation()


class MockShutdown:
    """Mock EC2Instance.shutdown."""
    is_shut_down = False

    def __call__(self):
        assert isinstance(self, MockShutdown)
        self.is_shut_down = True


def mock_log(*args):
    """Shut up the instance's log output."""
    pass


class Runnee:
    """A mock action for the EC2 instance to run."""
    has_run = False

    def __call__(self):
        self.has_run = True


class TestEC2Instance(TestCase):
    def setUp(self):
        session_name = MockSessionName()
        image = MockImage()
        instance_type = 'c1.xlarge'
        demo_networks = None
        account = MockAccount()
        from_scratch = None
        user_key = None
        login = None

        self.runnee = Runnee()

        self.shutdown_watcher = MockShutdown()

        self.instance = EC2Instance(
            session_name, image, instance_type, demo_networks, account,
            from_scratch, user_key, login)

        self.instance.shutdown = self.shutdown_watcher
        self.instance.log = mock_log

    def _runInstance(self, headless=False):
        """Set up and run a mock EC2 instance."""
        self.instance.set_up_and_run(False, not headless, self.runnee)

    def _hasStarted(self):
        """Did self.instance run its tests?"""
        return self.runnee.has_run

    def _hasShutDown(self):
        """Did self.instance shut down?"""
        return self.shutdown_watcher.is_shut_down

    def test_set_up_and_run_headful(self):
        # A non-headless run executes all tests in the instance, then
        # shuts down.
        self.assertFalse(self._hasStarted())
        self.assertFalse(self._hasShutDown())

        self._runInstance()

        self.assertTrue(self._hasStarted())
        self.assertTrue(self._hasShutDown())

    def test_set_up_and_run_headless(self):
        # An asynchronous, headless run kicks off the tests on the
        # instance but does not shut it down.
        self.assertFalse(self._hasStarted())
        self.assertFalse(self._hasShutDown())

        self._runInstance(headless=True)

        self.assertTrue(self._hasStarted())
        self.assertFalse(self._hasShutDown())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
