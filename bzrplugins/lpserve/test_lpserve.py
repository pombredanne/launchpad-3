# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import signal
import socket
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
    def start_service(test):
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
        # should we be doing thread.setDaemon(True) ?
        thread.start()
        new_service.service_started.wait(10.0)
        if not new_service.service_started.isSet():
            raise RuntimeError(
                'Failed to start the TestingLPServiceInAThread')
        test.addCleanup(new_service.stop_service)
        # what about returning new_service._sockname ?
        return new_service

    def stop_service(self):
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
        service = TestingLPServiceInAThread.start_service(self)
        service.stop_service()

    def test_multiple_stops(self):
        service = TestingLPServiceInAThread.start_service(self)
        service.stop_service()
        service.stop_service()

    def test_autostop(self):
        # We shouldn't leak a thread here, as it should be part of the test
        # case teardown.
        service = TestingLPServiceInAThread.start_service(self)


class TestCaseWithLPService(tests.TestCaseWithTransport):

    def setUp(self):
        super(TestCaseWithLPService, self).setUp()
        self.service = TestingLPServiceInAThread.start_service(self)

    def send_message_to_service(self, message):
        host, port = self.service._sockname
        addrs = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
            socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        (family, socktype, proto, canonname, sockaddr) = addrs[0]
        client_sock = socket.socket(family, socktype, proto)
        try:
            client_sock.connect(sockaddr)
            client_sock.sendall(message)
            response = client_sock.recv(1024)
        except socket.error, e:
            raise RuntimeError('Failed to connect: %s' % (e,))
        return response


class TestLPService(TestCaseWithLPService):

    def test_send_quit_message(self):
        response = self.send_message_to_service('quit\n')
        self.assertEqual('quit command requested... exiting\n', response)
        self.service.service_stopped.wait(10.0)
        self.assertTrue(self.service.service_stopped.isSet())

    def test_send_invalid_message_fails(self):
        response = self.send_message_to_service('unknown\n')
        self.assertStartsWith(response, 'FAILURE')


class TestCaseWithLPServiceSubprocess(tests.TestCaseWithTransport):
    """Tests will get a separate process to communicate to.

    The number of these tests should be small, because it is expensive to start
    and stop the daemon.

    TODO: This should probably use testresources, or layers somehow...
    """

    def setUp(self):
        super(TestCaseWithLPServiceSubprocess, self).setUp()
        self.service_process, self.service_port = self.start_service()
        self.addCleanup(self.stop_service)

    def send_message_to_service(self, message):
        host, port = self.service._sockname
        addrs = socket.getaddrinfo('localhost', self.service_port,
            socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        (family, socktype, proto, canonname, sockaddr) = addrs[0]
        client_sock = socket.socket(family, socktype, proto)
        try:
            client_sock.connect(sockaddr)
            client_sock.sendall(message)
            response = client_sock.recv(1024)
        except socket.error, e:
            raise RuntimeError('Failed to connect: %s' % (e,))
        return response

    def start_service(self):
        self.start_bzr_subprocess('lp-service')
        proc = self.run_bzr_subprocess(['lp-service', '--port', 'localhost:0'],
                skip_if_plan_to_signal=True)
        preload_line = proc.stderr.readline()
        self.assertStartsWith(preload_line, 'Preloading')
        prefix = 'Listening on port: '
        port_line = proc.stderr.readline()
        self.assertStartsWith(port_line, prefix)
        port = int(port_line[len(prefix):])
        return process, port

    def stop_service(self):
        if self.service_process is None:
            # Already stopped
            return
        # First, try to stop the service gracefully, by sending a 'quit'
        # message
        response = self.send_message_to_service('quit\n')
        tend = time.time() + 10.0
        while self.service_process.poll() is None:
            if time.time() > tend:
                self.finish_bzr_subprocess(process=self.service_process,
                    signal=signal.SIGINT, retcode=3)
                self.fail('Failed to quit gracefully after 10.0 seconds')
            time.sleep(0.1)
        self.assertEqual('quit command requested... exiting\n', response)

    def test_single_fork(self):
        pass
