
import threading

from bzrlib import tests, trace
from bzrlib.plugins import lpserve


class TestingLPServiceInAThread(lpserve.LPService):
    """Wrap starting and stopping an LPService instance in a thread."""

    # For testing, we set the timeouts much lower, because we want the tests to
    # run quickly
    WAIT_FOR_CHILDREN_TIMEOUT = 0.5
    SOCKET_TIMEOUT = 0.01
    SLEEP_FOR_CHILDREN_TIMEOUT = 0.01

    def __init__(self, host='127.0.0.1', port=0):
        self.service_started = threading.Event()
        self.service_stopped = threading.Event()
        self.this_thread = None
        super(TestingLPServiceInAThread, self).__init__(host=host, port=port)

    def _create_master_socket(self):
        trace.mutter('creating master socket')
        super(TestingLPServiceInAThread, self)._create_master_socket()
        trace.mutter('setting service_started')
        self.service_started.set()

    def main_loop(self):
        self.service_stopped.clear()
        super(TestingLPServiceInAThread, self).main_loop()
        self.service_stopped.set()

    @staticmethod
    def start(test):
        """Start a new LPService in a thread on a random port.

        This will block until the service has created its socket, and is ready
        to communicate.

        :return: A new TestingLPServiceInAThread instance
        """
        # Allocate a new port on only the loopback device
        new_service = TestingLPServiceInAThread()
        thread = threading.Thread(target=new_service.main_loop,
                                  name='TestingLPServiceInAThread')
        new_service.this_thread = thread
        thread.start()
        new_service.service_started.wait(10.0)
        if not new_service.service_started.isSet():
            raise RuntimeError(
                'Failed to start the TestingLPServiceInAThread')
        test.addCleanup(new_service.stop)
        # what about returning new_service._sockname ?
        return new_service

    def stop(self):
        """Stop the test-server thread. This can be called multiple times."""
        if self.this_thread is None:
            # We already stopped the process
            return
        self._should_terminate.set()
        self.service_stopped.wait(10.0)
        if not self.service_stopped.isSet():
            raise RuntimeError(
                'Failed to stop the TestingLPServiceInAThread')
        self.this_thread.join()
        # Break any refcycles
        self.this_thread = None


class TestTestingLPServiceInAThread(tests.TestCaseWithTransport):

    def test_start_and_stop_service(self):
        service = TestingLPServiceInAThread.start(self)
        service.stop()

    def test_multiple_stops(self):
        service = TestingLPServiceInAThread.start(self)
        service.stop()
        service.stop()

    def test_autostop(self):
        # We shouldn't leak a thread here
        service = TestingLPServiceInAThread.start(self)
