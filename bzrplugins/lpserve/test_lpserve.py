# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import signal
import socket
import subprocess
import tempfile
import threading
import time

from testtools import content

from bzrlib import (
    osutils,
    tests,
    trace,
    )
from bzrlib.plugins import lpserve

from canonical.config import config
from lp.codehosting import get_bzr_path, get_BZR_PLUGIN_PATH_for_subprocess


class TestingLPForkingServiceInAThread(lpserve.LPForkingService):
    """Wrap starting and stopping an LPForkingService instance in a thread."""

    # For testing, we set the timeouts much lower, because we want the tests to
    # run quickly
    WAIT_FOR_CHILDREN_TIMEOUT = 0.5
    SOCKET_TIMEOUT = 0.01
    SLEEP_FOR_CHILDREN_TIMEOUT = 0.01

    _fork_function = None

    def __init__(self, host='127.0.0.1', port=0):
        self.service_started = threading.Event()
        self.service_stopped = threading.Event()
        self.this_thread = None
        super(TestingLPForkingServiceInAThread, self).__init__(host=host,
                                                               port=port)

    def _create_master_socket(self):
        trace.mutter('creating master socket')
        super(TestingLPForkingServiceInAThread, self)._create_master_socket()
        trace.mutter('setting service_started')
        self.service_started.set()

    def main_loop(self):
        self.service_stopped.clear()
        super(TestingLPForkingServiceInAThread, self).main_loop()
        self.service_stopped.set()

    def fork_one_request(self, conn, client_addr, command):
        # We intentionally don't allow the test suite to request a fork, as
        # threads + forks and everything else don't exactly play well together
        raise NotImplementedError(self.fork_one_request)

    @staticmethod
    def start_service(test):
        """Start a new LPForkingService in a thread on a random port.

        This will block until the service has created its socket, and is ready
        to communicate.

        :return: A new TestingLPForkingServiceInAThread instance
        """
        # Allocate a new port on only the loopback device
        new_service = TestingLPForkingServiceInAThread()
        thread = threading.Thread(target=new_service.main_loop,
                                  name='TestingLPForkingServiceInAThread')
        new_service.this_thread = thread
        # should we be doing thread.setDaemon(True) ?
        thread.start()
        new_service.service_started.wait(10.0)
        if not new_service.service_started.isSet():
            raise RuntimeError(
                'Failed to start the TestingLPForkingServiceInAThread')
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
                'Failed to stop the TestingLPForkingServiceInAThread')
        self.this_thread.join()
        # Break any refcycles
        self.this_thread = None


class TestTestingLPForkingServiceInAThread(tests.TestCaseWithTransport):

    def test_start_and_stop_service(self):
        service = TestingLPForkingServiceInAThread.start_service(self)
        service.stop_service()

    def test_multiple_stops(self):
        service = TestingLPForkingServiceInAThread.start_service(self)
        service.stop_service()
        service.stop_service()

    def test_autostop(self):
        # We shouldn't leak a thread here, as it should be part of the test
        # case teardown.
        service = TestingLPForkingServiceInAThread.start_service(self)


class TestCaseWithLPForkingService(tests.TestCaseWithTransport):

    def setUp(self):
        super(TestCaseWithLPForkingService, self).setUp()
        self.service = TestingLPForkingServiceInAThread.start_service(self)

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


class TestLPForkingServiceCommandToArgv(tests.TestCase):

    def assertAsArgv(self, argv, command_str):
        self.assertEqual(argv,
            lpserve.LPForkingService.command_to_argv(command_str))

    def test_simple(self):
        self.assertAsArgv([u'foo'], 'foo')
        self.assertAsArgv([u'foo', u'bar'], 'foo bar')

    def test_quoted(self):
        self.assertAsArgv([u'foo'], 'foo')
        self.assertAsArgv([u'foo bar'], '"foo bar"')

    def test_unicode(self):
        self.assertAsArgv([u'command', u'\xe5'], 'command \xc3\xa5')


class TestLPForkingService(TestCaseWithLPForkingService):

    def test_send_quit_message(self):
        response = self.send_message_to_service('quit\n')
        self.assertEqual('ok\nquit command requested... exiting\n', response)
        self.service.service_stopped.wait(10.0)
        self.assertTrue(self.service.service_stopped.isSet())

    def test_send_invalid_message_fails(self):
        response = self.send_message_to_service('unknown\n')
        self.assertStartsWith(response, 'FAILURE')

    def test_send_hello_heartbeat(self):
        response = self.send_message_to_service('hello\n')
        self.assertEqual('ok\nyep, still alive\n', response)


class TestCaseWithSubprocess(tests.TestCaseWithTransport):
    """Override the bzr start_bzr_subprocess command.

    The launchpad infrastructure requires a fair amount of configuration to get
    paths, etc correct. So this provides that work.
    """

    def get_python_path(self):
        """Return the path to the Python interpreter."""
        return '%s/bin/py' % config.root

    def start_bzr_subprocess(self, process_args, env_changes=None,
                             working_dir=None):
        """Start bzr in a subprocess for testing.

        Copied and modified from `bzrlib.tests.TestCase.start_bzr_subprocess`.
        This version removes some of the skipping stuff, some of the
        irrelevant comments (e.g. about win32) and uses Launchpad's own
        mechanisms for getting the path to 'bzr'.

        Comments starting with 'LAUNCHPAD' are comments about our
        modifications.
        """
        if env_changes is None:
            env_changes = {}
        env_changes['BZR_PLUGIN_PATH'] = get_BZR_PLUGIN_PATH_for_subprocess()
        old_env = {}

        def cleanup_environment():
            for env_var, value in env_changes.iteritems():
                old_env[env_var] = osutils.set_or_unset_env(env_var, value)

        def restore_environment():
            for env_var, value in old_env.iteritems():
                osutils.set_or_unset_env(env_var, value)

        cwd = None
        if working_dir is not None:
            cwd = osutils.getcwd()
            os.chdir(working_dir)

        # LAUNCHPAD: Because of buildout, we need to get a custom Python
        # binary, not sys.executable.
        python_path = self.get_python_path()
        # LAUNCHPAD: We can't use self.get_bzr_path(), since it'll find
        # lib/bzrlib, rather than the path to sourcecode/bzr/bzr.
        bzr_path = get_bzr_path()
        try:
            cleanup_environment()
            command = [python_path, bzr_path]
            command.extend(process_args)
            process = self._popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        finally:
            restore_environment()
            if cwd is not None:
                os.chdir(cwd)

        return process


class TestCaseWithLPForkingServiceSubprocess(TestCaseWithSubprocess):
    """Tests will get a separate process to communicate to.

    The number of these tests should be small, because it is expensive to start
    and stop the daemon.

    TODO: This should probably use testresources, or layers somehow...
    """

    def setUp(self):
        super(TestCaseWithLPForkingServiceSubprocess, self).setUp()
        self.service_process, self.service_port = self.start_service_subprocess()
        self.addCleanup(self.stop_service)

    def start_conversation(self, message):
        """Start talking to the service, and get the initial response."""
        addrs = socket.getaddrinfo('127.0.0.1', self.service_port,
            socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        (family, socktype, proto, canonname, sockaddr) = addrs[0]
        client_sock = socket.socket(family, socktype, proto)
        trace.mutter('sending %r to port %s' % (message, self.service_port))
        try:
            client_sock.connect(sockaddr)
            client_sock.sendall(message)
            response = client_sock.recv(1024)
        except socket.error, e:
            raise RuntimeError('Failed to connect: %s' % (e,))
        trace.mutter('response: %r' % (response,))
        if response.startswith("FAILURE"):
            raise RuntimeError('Failed to send message: %r' % (response,))
        return response, client_sock

    def send_message_to_service(self, message):
        response, client_sock = self.start_conversation(message)
        client_sock.close()
        return response

    def send_fork_request(self, command):
        response, sock = self.start_conversation('fork %s\n' % (command,))
        ok, pid, path, tail = response.split('\n')
        self.assertEqual('ok', ok)
        self.assertEqual('', tail)
        # Don't really care what it is, but should be an integer
        pid = int(pid)
        path = path.strip()
        self.assertContainsRe(path, '/lp-forking-service-child-')
        return path, pid, sock

    def start_service_subprocess(self):
        # Make sure this plugin is exposed to the subprocess
        # SLOOWWW (~2.4 seconds, which is why we are doing the work anyway)
        fd, tempname = tempfile.mkstemp(prefix='tmp-log-bzr-lp-forking-')
        # I'm not 100% sure about when cleanup runs versus addDetail, but I
        # think this will work.
        self.addCleanup(os.remove, tempname)
        def read_log():
            f = os.fdopen(fd)
            f.seek(0)
            content = f.read()
            f.close()
            return [content]
        self.addDetail('server-log', content.Content(
            content.ContentType('text', 'plain', {"charset": "utf8"}),
            read_log))
        env_changes = {'BZR_PLUGIN_PATH': lpserve.__path__[0],
                       'BZR_LOG': tempname}
        proc = self.start_bzr_subprocess(
            ['lp-service', '--port', '127.0.0.1:0', '--no-preload',
             '--children-timeout=1'],
            env_changes=env_changes)
        trace.mutter('started lp-service subprocess')
        # preload_line = proc.stderr.readline()
        # self.assertStartsWith(preload_line, 'Preloading')
        prefix = 'Listening on port: '
        port_line = proc.stderr.readline()
        self.assertStartsWith(port_line, prefix)
        port = int(port_line[len(prefix):])
        trace.mutter(port_line)
        return proc, port

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
                    send_signal=signal.SIGINT, retcode=3)
                self.fail('Failed to quit gracefully after 10.0 seconds')
            time.sleep(0.1)
        self.assertEqual('ok\nquit command requested... exiting\n', response)

    def _get_fork_handles(self, path):
        trace.mutter('getting handles for: %s' % (path,))
        stdin_path = os.path.join(path, 'stdin')
        stdout_path = os.path.join(path, 'stdout')
        stderr_path = os.path.join(path, 'stderr')
        # Consider the ordering, the other side should open 'stdin' first, but
        # we want it to block until we open the last one, or we race and it can
        # delete the other handles before we get to open them.
        child_stdin = open(stdin_path, 'wb')
        child_stdout = open(stdout_path, 'rb')
        child_stderr = open(stderr_path, 'rb')
        return child_stdin, child_stdout, child_stderr

    def communicate_with_fork(self, path, stdin=None):
        child_stdin, child_stdout, child_stderr = self._get_fork_handles(path)
        if stdin is not None:
            child_stdin.write(stdin)
        child_stdin.close()
        stdout_content = child_stdout.read()
        stderr_content = child_stderr.read()
        return stdout_content, stderr_content

    def assertReturnCode(self, expected_code, sock):
        """Assert that we get the expected return code as a message."""
        response = sock.recv(1024)
        self.assertStartsWith(response, 'exited\n')
        code = int(response.split('\n', 1)[1])
        self.assertEqual(expected_code, code)

    def test_fork_lp_serve_hello(self):
        path, _, sock = self.send_fork_request('lp-serve --inet 2')
        stdout_content, stderr_content = self.communicate_with_fork(path,
            'hello\n')
        self.assertEqual('ok\x012\n', stdout_content)
        self.assertEqual('', stderr_content)
        self.assertReturnCode(0, sock)

    def test_fork_replay(self):
        path, _, sock = self.send_fork_request('launchpad-replay')
        stdout_content, stderr_content = self.communicate_with_fork(path,
            '1 hello\n2 goodbye\n1 maybe\n')
        self.assertEqualDiff('hello\nmaybe\n', stdout_content)
        self.assertEqualDiff('goodbye\n', stderr_content)
        self.assertReturnCode(0, sock)

    def test_just_run_service(self):
        # Start and stop are defined in setUp()
        pass

    def test_fork_multiple_children(self):
        paths = []
        for idx in range(4):
            paths.append(self.send_fork_request('launchpad-replay'))
        for idx in [3, 2, 0, 1]:
            p, pid, sock = paths[idx]
            stdout_msg = 'hello %d\n' % (idx,)
            stderr_msg = 'goodbye %d\n' % (idx+1,)
            stdout, stderr = self.communicate_with_fork(p,
                '1 %s2 %s' % (stdout_msg, stderr_msg))
            self.assertEqualDiff(stdout_msg, stdout)
            self.assertEqualDiff(stderr_msg, stderr)
            self.assertReturnCode(0, sock)
