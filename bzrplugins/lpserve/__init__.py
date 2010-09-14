# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bazaar plugin to run the smart server on Launchpad.

Cribbed from bzrlib.builtins.cmd_serve from Bazaar 0.16.
"""

__metaclass__ = type

__all__ = ['cmd_launchpad_server',
           'cmd_launchpad_forking_service',
          ]


import errno
import os
import resource
import shlex
import shutil
import signal
import socket
import sys
import tempfile
import threading
import time

from bzrlib.commands import Command, register_command
from bzrlib.option import Option
from bzrlib import commands, errors, lockdir, ui, trace

from bzrlib.smart import medium, server
from bzrlib.transport import get_transport


class cmd_launchpad_server(Command):
    """Run a Bazaar server that maps Launchpad branch URLs to the internal
    file-system format.
    """

    aliases = ['lp-serve']

    takes_options = [
        Option('inet',
               help='serve on stdin/out for use from inetd or sshd'),
        Option('port',
               help='listen for connections on nominated port of the form '
                    '[hostname:]portnumber. Passing 0 as the port number will'
                    ' result in a dynamically allocated port. Default port is'
                    ' 4155.',
               type=str),
        Option('upload-directory',
               help='upload branches to this directory. Defaults to '
                    'config.codehosting.hosted_branches_root.',
               type=unicode),
        Option('mirror-directory',
               help='serve branches from this directory. Defaults to '
                    'config.codehosting.mirrored_branches_root.'),
        Option('codehosting-endpoint',
               help='the url of the internal XML-RPC server. Defaults to '
                    'config.codehosting.codehosting_endpoint.',
               type=unicode),
        ]

    takes_args = ['user_id']

    def get_smart_server(self, transport, port, inet):
        """Construct a smart server."""
        if inet:
            smart_server = medium.SmartServerPipeStreamMedium(
                sys.stdin, sys.stdout, transport)
        else:
            host = medium.BZR_DEFAULT_INTERFACE
            if port is None:
                port = medium.BZR_DEFAULT_PORT
            else:
                if ':' in port:
                    host, port = port.split(':')
                port = int(port)
            smart_server = server.SmartTCPServer(
                transport, host=host, port=port)
            print 'listening on port: ', smart_server.port
            sys.stdout.flush()
        return smart_server

    def run_server(self, smart_server):
        """Run the given smart server."""
        # for the duration of this server, no UI output is permitted.
        # note that this may cause problems with blackbox tests. This should
        # be changed with care though, as we dont want to use bandwidth
        # sending progress over stderr to smart server clients!
        old_factory = ui.ui_factory
        try:
            ui.ui_factory = ui.SilentUIFactory()
            smart_server.serve()
        finally:
            ui.ui_factory = old_factory

    def run(self, user_id, port=None, branch_directory=None,
            codehosting_endpoint_url=None, inet=False):
        from lp.codehosting.bzrutils import install_oops_handler
        from lp.codehosting.vfs import get_lp_server, hooks
        install_oops_handler(user_id)
        four_gig = int(4e9)
        resource.setrlimit(resource.RLIMIT_AS, (four_gig, four_gig))
        seen_new_branch = hooks.SetProcTitleHook()
        lp_server = get_lp_server(
            int(user_id), codehosting_endpoint_url, branch_directory,
            seen_new_branch.seen)
        lp_server.start_server()

        old_lockdir_timeout = lockdir._DEFAULT_TIMEOUT_SECONDS
        try:
            lp_transport = get_transport(lp_server.get_url())
            smart_server = self.get_smart_server(lp_transport, port, inet)
            lockdir._DEFAULT_TIMEOUT_SECONDS = 0
            self.run_server(smart_server)
        finally:
            lockdir._DEFAULT_TIMEOUT_SECONDS = old_lockdir_timeout
            lp_server.stop_server()


register_command(cmd_launchpad_server)


class LPForkingService(object):
    """A class encapsulating the state of the LP Service."""

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 4156
    WAIT_FOR_CHILDREN_TIMEOUT = 5*60 # Wait no more than 5 min for children
    SOCKET_TIMEOUT = 1.0
    SLEEP_FOR_CHILDREN_TIMEOUT = 1.0

    _fork_function = os.fork

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        if host is None:
            self.host = self.DEFAULT_HOST
        else:
            self.host = host
        if port is None:
            self.port = self.DEFAULT_PORT
        else:
            self.port = port
        self._start_time = time.time()
        self._should_terminate = threading.Event()
        # We address these locally, in case of shutdown socket may be gc'd
        # before we are
        self._socket_timeout = socket.timeout
        self._socket_error = socket.error
        self._socket_timeout = socket.timeout
        self._socket_error = socket.error
        # Map from pid => information
        self._child_processes = {}
        self._children_spawned = 0

    def _create_master_socket(self):
        addrs = socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC,
            socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[0]
        (family, socktype, proto, canonname, sockaddr) = addrs
        self._server_socket = socket.socket(family, socktype, proto)
        if sys.platform != 'win32':
            self._server_socket.setsockopt(socket.SOL_SOCKET,
                socket.SO_REUSEADDR, 1)
        try:
            self._server_socket.bind(sockaddr)
        except self._socket_error, message:
            raise errors.CannotBindAddress(self.host, self.port, message)
        self._sockname = self._server_socket.getsockname()
        # self.host = self._sockname[0]
        self.port = self._sockname[1]
        self._server_socket.listen(5)
        self._server_socket.settimeout(self.SOCKET_TIMEOUT)
        trace.mutter('set socket timeout to: %s' % (self.SOCKET_TIMEOUT,))

    def _handle_sigchld(self, signum, frm):
        # While we are running, disable this as a handler, so we don't
        # re-enter
        signal.signal(signal.SIGCHLD, self._prev_sigchld_handler)
        try:
            if (self._prev_sigchld_handler is not None
                and callable(self._prev_sigchld_handler)):
                # self._prev_sigchld_handler may be 0 or 1, etc if the previous
                # handling was IGNORE or DEFAULT, etc.
                self._prev_sigchld_handler(signum, frm)
        finally:
            signal.signal(signal.SIGCHLD, self._handle_sigchld)

    def _register_sigchld(self):
        """Register a SIGCHILD handler.

        If we have a trigger for SIGCHILD then we can quickly respond to
        clients when their process exits. The main risk is getting more EAGAIN
        errors elsewhere.
        """
        # We register a dummy function, because all we really care about is
        # interrupting the '.accept()' call.
        self._prev_sigchld_handler = signal.signal(signal.SIGCHLD,
                                                   self._handle_sigchld)

    def _unregister_sigchld(self):
        if self._prev_sigchld_handler is None:
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        else:
            signal.signal(signal.SIGCHLD, self._prev_sigchld_handler)
        self._prev_sigchld_handler = None

    def _create_child_file_descriptors(self, base_path):
        stdin_path = os.path.join(base_path, 'stdin')
        stdout_path = os.path.join(base_path, 'stdout')
        stderr_path = os.path.join(base_path, 'stderr')
        os.mkfifo(stdin_path)
        os.mkfifo(stdout_path)
        os.mkfifo(stderr_path)

    def _bind_child_file_descriptors(self, base_path):
        import logging
        from bzrlib import ui
        stdin_path = os.path.join(base_path, 'stdin')
        stdout_path = os.path.join(base_path, 'stdout')
        stderr_path = os.path.join(base_path, 'stderr')
        # Opening for writing blocks (or fails), so do those last
        # TODO: Consider buffering...
        stdin_fid = os.open(stdin_path, os.O_RDONLY | os.O_NONBLOCK)
        stdout_fid = os.open(stdout_path, os.O_WRONLY)
        stderr_fid = os.open(stderr_path, os.O_WRONLY)
        # XXX: Cheap hack. by this point bzrlib has opened stderr for logging
        #      (as part of starting the service process in the first place). As
        #      such, it has a stream handler that writes to stderr. logging
        #      tries to flush and close that, but the file is already closed.
        #      This just supresses that exception
        logging.raiseExceptions = False
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
        os.dup2(stdin_fid, 0)
        os.dup2(stdout_fid, 1)
        os.dup2(stderr_fid, 2)
        sys.stdin = os.fdopen(stdin_fid, 'rb')
        sys.stdout = os.fdopen(stdout_fid, 'wb')
        sys.stderr = os.fdopen(stderr_fid, 'wb')
        ui.ui_factory.stdin = sys.stdin
        ui.ui_factory.stdout = sys.stdout
        ui.ui_factory.stderr = sys.stderr
        # Now that we've opened the handles, delete everything so that we don't
        # leave garbage around. Because the open() is done in blocking mode, we
        # know that someone has already connected to them, and we don't want
        # anyone else getting confused and connecting.
        os.remove(stderr_path)
        os.remove(stdout_path)
        os.remove(stdin_path)
        os.rmdir(base_path)

    def _close_child_file_descriptons(self):
        sys.stdin.close()
        sys.stderr.close()
        sys.stdout.close()

    def become_child(self, command_argv, path):
        """We are in the spawned child code, do our magic voodoo."""
        # Stop tracking SIGCHILD, we don't want it to confuse the child
        self._unregister_sigchld()
        # Reset the start time
        trace._bzr_log_start_time = time.time()
        trace.mutter('%d starting %r'
                     % (os.getpid(), command_argv,))
        self.host = None
        self.port = None
        self._sockname = None
        self._bind_child_file_descriptors(path)
        self._run_child_command(command_argv)

    def _run_child_command(self, command_argv):
        # This is the point where we would actually want to do something with
        # our life
        retcode = commands.run_bzr_catch_errors(command_argv)
        self._close_child_file_descriptons()
        trace.mutter('%d finished %r'
                     % (os.getpid(), command_argv,))
        # We force os._exit() here, because we don't want to unwind the stack,
        # which has complex results. (We can get it to unwind back to the
        # cmd_launchpad_forking_service code, and even back to main() reporting
        # thereturn code, but after that, suddenly the return code changes from
        # a '0' to a '1', with no logging of info.
        # TODO: Should we call sys.exitfunc() here? it allows atexit functions
        #       to fire, however, some of those may be still around from the
        #       parent process, which we don't really want.
        ## sys.exitfunc()
        os._exit(retcode)

    @staticmethod
    def command_to_argv(command_str):
        """Convert a 'foo bar' style command to [u'foo', u'bar']"""
        # command_str must be a utf-8 string
        return [s.decode('utf-8') for s in shlex.split(command_str)]

    def fork_one_request(self, conn, client_addr, command_argv):
        """Fork myself and serve a request."""
        temp_name = tempfile.mkdtemp(prefix='lp-forking-service-child-')
        self._create_child_file_descriptors(temp_name)
        # Now that we've set everything up, send the response to the client we
        # create them first, so the client can start trying to connect to them,
        # while we fork and have the child do the same.
        self._children_spawned += 1
        pid = self._fork_function()
        if pid == 0:
            pid = os.getpid()
            trace.mutter('%d spawned' % (pid,))
            self._server_socket.close()
            conn.sendall('ok\n%d\n%s\n' % (pid, temp_name))
            conn.close()
            self.become_child(command_argv, temp_name)
            trace.warning('become_child returned!!!')
            sys.exit(1)
        else:
            self._child_processes[pid] = (temp_name, conn)
            self.log(client_addr, 'Spawned process %s for %r: %s'
                            % (pid, command_argv, temp_name))

    def main_loop(self):
        self._should_terminate.clear()
        self._create_master_socket()
        self._register_sigchld()
        trace.note('Listening on port: %s' % (self.port,))
        while not self._should_terminate.isSet():
            try:
                conn, client_addr = self._server_socket.accept()
            except self._socket_timeout:
                # Check on the children, etc.
                pass
            except self._socket_error, e:
                if e.args[0] == errno.EINTR:
                    # EINTR just means we got a signal like SIGCHLD, poll and
                    # try again
                    pass
                elif e.args[0] != errno.EBADF:
                    # We can get EBADF here while we are shutting down
                    # So we just ignore it for now
                    pass
                else:
                    # Log any other failure mode
                    trace.warning("listening socket error: %s", e)
            else:
                self.log(client_addr, 'connected')
                self.serve_one_connection(conn, client_addr)
            self._poll_children()
        trace.note('Shutting down. Waiting up to %.0fs for %d child processes'
                   % (self.WAIT_FOR_CHILDREN_TIMEOUT,
                      len(self._child_processes),))
        self._shutdown_children()
        trace.note('Exiting')

    def log(self, client_addr, message):
        """Log a message to the trace log.

        Include the information about what connection is being served.
        """
        if client_addr is not None:
            # Note, we don't use conn.getpeername() because if a client
            # disconnects before we get here, that raises an exception
            peer_host, peer_port = client_addr
            conn_info = '[%s:%d] ' % (peer_host, peer_port)
        else:
            conn_info = ''
        trace.mutter('%s%s' % (conn_info, message))

    def log_information(self):
        """Log the status information.

        This includes stuff like number of children, and ... ?
        """
        self._poll_children()
        self.log(None, 'Running for %.3fs' % (time.time() - self._start_time))
        self.log(None, '%d children currently running (spawned %d total)'
                       % (len(self._child_processes), self._children_spawned))
        # Read the current information about memory consumption, etc.
        self.log(None, 'Self: %s'
                       % (resource.getrusage(resource.RUSAGE_SELF),))
        # This seems to be the sum of all rusage for all children that have
        # been collected (not for currently running children, or ones we
        # haven't "wait"ed on.) We may want to read /proc/PID/status, since
        # 'live' information is probably more useful.
        self.log(None, 'Finished children: %s'
                       % (resource.getrusage(resource.RUSAGE_CHILDREN),))

    def _poll_children(self):
        """See if children are still running, etc.

        One interesting hook here would be to track memory consumption, etc.
        """
        to_remove = []
        # TODO: I think we can change this to a simple 'while True: (c_pid,
        # status) = os.wait() if c_pid == 0: break. But that needs some
        # testing.
        while self._child_processes:
            try:
                c_id, exit_code, rusage = os.wait3(os.WNOHANG)
            except OSError, e:
                if e.errno == errno.ECHILD:
                    # TODO: We handle this right now because the test suite
                    #       fakes a child, since we wanted to test some code
                    #       without actually forking anything
                    trace.mutter('_poll_children() called, and'
                        ' self._child_processes indicates there are'
                        ' children, but os.wait3() says there are not.'
                        ' current_children: %s' % (self._child_processes,))
                    return
            if c_id == 0:
                # No more children stopped right now
                return
            c_path, sock = self._child_processes.pop(c_id)
            trace.mutter('%s exited %s and usage: %s'
                         % (c_id, exit_code, rusage))
            try:
                sock.sendall('exited\n%s\n' % (exit_code,))
            except (self._socket_timeout, self._socket_error), e:
                # The client disconnected before we wanted them to,
                # no big deal
                trace.mutter('%s\'s socket already closed: %s' % (c_id, e))
            else:
                sock.close()
            if os.path.exists(c_path):
                # The child failed to cleanup after itself, do the work here
                trace.warning('Had to clean up after child %d: %s\n'
                              % (c_id, c_path))
                shutil.rmtree(c_path)

    def _wait_for_children(self, secs):
        start = time.time()
        end = start + secs
        while self._child_processes:
            self._poll_children()
            if secs > 0 and time.time() > end:
                break
            time.sleep(self.SLEEP_FOR_CHILDREN_TIMEOUT)

    def _shutdown_children(self):
        self._wait_for_children(self.WAIT_FOR_CHILDREN_TIMEOUT)
        if self._child_processes:
            trace.warning('Failed to stop children: %s'
                % ', '.join(map(str, self._child_processes)))
            for c_id in self._child_processes:
                trace.warning('sending SIGINT to %d' % (c_id,))
                os.kill(c_id, signal.SIGINT)
            # We sent the SIGINT signal, see if they exited
            self._wait_for_children(self.SLEEP_FOR_CHILDREN_TIMEOUT)
        if self._child_processes:
            # No? Then maybe something more powerful
            for c_id in self._child_processes:
                trace.warning('sending SIGKILL to %d' % (c_id,))
                os.kill(c_id, signal.SIGKILL)
            # We sent the SIGKILL signal, see if they exited
            self._wait_for_children(self.SLEEP_FOR_CHILDREN_TIMEOUT)
        if self._child_processes:
            for c_id, (c_path, sock) in self._child_processes.iteritems():
                # TODO: We should probably put something into this message?
                #       However, the likelyhood is very small that this isn't
                #       already closed because of SIGKILL + _wait_for_children
                #       And I don't really know what to say...
                sock.close()
                if os.path.exists(c_path):
                    trace.warning('Cleaning up after immortal child %d: %s\n'
                                  % (c_id, c_path))
                    shutil.rmtree(c_path)

    def serve_one_connection(self, conn, client_addr):
        request = conn.recv(1024);
        request = request.strip()
        self.log(client_addr, 'request: %r' % (request,))
        if request == 'hello':
            conn.sendall('ok\nyep, still alive\n')
            self.log_information()
        elif request == 'quit':
            self._should_terminate.set()
            conn.sendall('ok\nquit command requested... exiting\n')
        elif request.startswith('fork '):
            command = request[5:]
            try:
                command_argv = self.command_to_argv(command)
            except Exception, e:
                # TODO: Log the traceback?
                self.log(client_addr, 'command parsing failed: %r'
                                      % (str(e),))
                conn.sendall('FAILURE\ncommand parsing failed: %r'
                             % (str(e),))
            else:
                self.log(client_addr, 'fork requested for %r' % (command,))
                # TODO: Do we want to limit the number of children? And/or
                #       prefork additional instances? (the design will need to
                #       change if we prefork and run arbitrary commands.)
                self.fork_one_request(conn, client_addr, command_argv)
                # We don't close the conn normally, since we will report the
                # exit status later
                return
        else:
            self.log(client_addr, 'FAILURE: unknown request: %r' % (request,))
            # TODO: Do we want to be friendly here? Or do we want to just
            #       ignore the request? This is meant to be a local-only
            #       process, so we probably want to be helpful
            conn.sendall('FAILURE\nunknown request: %r\n' % (request,))
        conn.close()


class cmd_launchpad_forking_service(Command):
    """Launch a long-running process, where you can ask for new processes.

    The process will block on a given --port waiting for requests to be made.
    When a request is made, it will fork itself and redirect stdout/in/err to
    fifos on the filesystem, and start running the requseted command. The
    caller will be informed where those file handles can be found. Thus it only
    makes sense that the process connecting to the port must be on the same
    system.
    """

    aliases = ['lp-service']

    takes_options = [Option('port',
                        help='Listen for connections on [host:]portnumber',
                        type=str),
                     Option('preload',
                        help="Do/don't preload libraries before startup."),
                     Option('children-timeout', type=int,
                        help="Only wait XX seconds for children to exit"),
                    ]

    def _preload_libraries(self):
        global libraries_to_preload
        for pyname in libraries_to_preload:
            try:
                __import__(pyname)
            except ImportError, e:
                trace.mutter('failed to preload %s: %s' % (pyname, e))

    def _get_host_and_port(self, port):
        host = None
        if port is not None:
            if ':' in port:
                host, port = port.rsplit(':', 1)
            port = int(port)
        return host, port

    def run(self, port=None, preload=True,
            children_timeout=LPForkingService.WAIT_FOR_CHILDREN_TIMEOUT):
        host, port = self._get_host_and_port(port)
        if preload:
            # We note this because it often takes a fair amount of time.
            trace.note('Preloading %d modules' % (len(libraries_to_preload),))
            self._preload_libraries()
        service = LPForkingService(host, port)
        service.WAIT_FOR_CHILDREN_TIMEOUT = children_timeout
        service.main_loop()

register_command(cmd_launchpad_forking_service)


class cmd_launchpad_replay(Command):
    """Write input from stdin back to stdout or stderr.

    This is a hidden command, primarily available for testing
    cmd_launchpad_forking_service.
    """

    hidden = True

    def run(self):
        # Just read line-by-line from stdin, and write out to stdout or stderr
        # depending on the prefix
        for line in sys.stdin:
            channel, contents = line.split(' ', 1)
            channel = int(channel)
            if channel == 1:
                sys.stdout.write(contents)
                sys.stdout.flush()
            elif channel == 2:
                sys.stderr.write(contents)
                sys.stderr.flush()
            else:
                raise RuntimeError('Invalid channel request.')
        return 0

register_command(cmd_launchpad_replay)

libraries_to_preload = [
    'bzrlib.errors',
    'bzrlib.repofmt.groupcompress_repo',
    'bzrlib.repository',
    'bzrlib.smart',
    'bzrlib.smart.protocol',
    'bzrlib.smart.request',
    'bzrlib.smart.server',
    'bzrlib.smart.vfs',
    'bzrlib.transport.local',
    'bzrlib.transport.readonly',
    'lp.codehosting.bzrutils',
    'lp.codehosting.vfs',
    'lp.codehosting.vfs.branchfs',
    'lp.codehosting.vfs.branchfsclient',
    'lp.codehosting.vfs.hooks',
    'lp.codehosting.vfs.transport',
    ]



def load_tests(standard_tests, module, loader):
    standard_tests.addTests(loader.loadTestsFromModuleNames(
        [__name__ + '.' + x for x in [
            'test_lpserve',
        ]]))
    return standard_tests
