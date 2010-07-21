# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bazaar plugin to run the smart server on Launchpad.

Cribbed from bzrlib.builtins.cmd_serve from Bazaar 0.16.
"""

__metaclass__ = type

__all__ = ['cmd_launchpad_server']


import errno
import os
import resource
import shutil
import socket
import sys
import tempfile
import time

from bzrlib.commands import Command, register_command
from bzrlib.option import Option
from bzrlib import errors, lockdir, ui, trace

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


class LPService(object):
    """A class encapsulating the state of the LP Service."""

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 4156
    WAIT_FOR_CHILDREN_TIMEOUT = 5*60 # Wait no more than 5 min for children

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        if host is None:
            self.host = self.DEFAULT_HOST
        else:
            self.host = host
        if port is None:
            self.port = self.DEFAULT_PORT
        else:
            self.port = port
        self._should_terminate = False
        # We address these locally, in case of shutdown socket may be gc'd
        # before we are
        self._socket_timeout = socket.timeout
        self._socket_error = socket.error
        self._socket_timeout = socket.timeout
        self._socket_error = socket.error
        # Map from pid => information
        self._child_processes = {}

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
            raise errors.CannotBindAddress(host, port, message)
        self._sockname = self._server_socket.getsockname()
        # self.host = self._sockname[0]
        self.port = self._sockname[1]
        self._server_socket.listen(1)
        self._server_socket.settimeout(1)

    def _setup_child_file_descriptors(self, base_path):
        stdin_path = os.path.join(base_path, 'stdin')
        stdout_path = os.path.join(base_path, 'stdout')
        stderr_path = os.path.join(base_path, 'stderr')
        os.mkfifo(stdin_path)
        os.mkfifo(stdout_path)
        os.mkfifo(stderr_path)
        # Opening for writing blocks (or fails), so do those last
        # TODO: Consider buffering...
        stdin_fid = os.open(stdin_path, os.O_RDONLY | os.O_NONBLOCK)
        stdout_fid = os.open(stdout_path, os.O_WRONLY)
        stderr_fid = os.open(stdout_path, os.O_WRONLY)
        sys.stdin.close()
        sys.stdout.close()
        # sys.stderr.close()
        os.dup2(stdin_fid, 0)
        os.dup2(stdout_fid, 1)
        os.dup2(stderr_fid, 2)
        # We don't actually have to do this, because the stdin/stdout/stderr
        # objects will already talk to the right handles because dup2 replaces
        # the low-level I/O (probably wouldn't do exactly the same on win32)
        # sys.stdin = os.fdopen(stdin_fid, 'rb')
        # sys.stdout = os.fdopen(stdout_fid, 'wb')
        # sys.stderr = os.fdopen(stderr_fid, 'wb')
        # Now that we've opened the handles, delete everything so that we don't
        # leave garbage around. Because the open() is done in blocking mode, we
        # know that someone has already connected to them, and we don't want
        # anyone else getting confused and connecting.
        os.remove(stderr_path)
        os.remove(stdout_path)
        os.remove(stdin_path)
        os.rmdir(base_path)

    def become_child(self, path):
        """We are in the spawned child code, do our magic voodoo."""
        self._setup_child_file_descriptors(path)
        # This is the point where we would actually want to do something with
        # our life
        sys.exit(0)

    def fork_one_request(self, conn, user_id):
        """Fork myself and serve a request."""
        temp_name = tempfile.mkdtemp(prefix='lp-service-child-')
        pid = os.fork()
        if pid == 0:
            # Child process, close the connections
            conn.sendall(temp_name + '\n')
            conn.close()
            self._server_socket.close()
            self.host = None
            self.port = None
            self._sockname = None
            self.become_child(temp_name)
            trace.warning('become_child returned!!!')
            sys.exit(1)
        else:
            self._child_processes[pid] = temp_name
            self.log(conn, 'Spawned process %s for user %r: %s'
                            % (pid, user_id, temp_name))

    def main_loop(self):
        self._create_master_socket()
        trace.note('Connected to: %s' % (self._sockname,))
        self._should_terminate = False
        while not self._should_terminate:
            try:
                conn, client_addr = self._server_socket.accept()
            except self._socket_timeout:
                # Check on the children, and see if we think we should quit
                # anyway
                self._poll_children()
            except self._socket_error, e:
                # we might get a EBADF here, any other socket errors
                # should get logged.
                if e.args[0] != errno.EBADF:
                    trace.warning("listening socket error: %s", e)
            else:
                self.log(conn, 'connected')
                self.serve_one_connection(conn)
                if self._should_terminate:
                    break
        trace.note('Shutting down. Waiting up to %.0fs for %d child processes'
                   % (self.WAIT_FOR_CHILDREN_TIMEOUT,
                      len(self._child_processes),))
        self._wait_for_children()
        trace.note('Exiting')

    def log(self, conn, message):
        """Log a message to the trace log.

        Include the information about what connection is being served.
        """
        if conn is not None:
            peer_host, peer_port = conn.getpeername()
            conn_info = '[%s:%d] ' % (peer_host, peer_port)
        else:
            conn_info = ''
        trace.mutter('%s%s' % (conn_info, message))

    def log_information(self):
        """Log the status information.

        This includes stuff like number of children, and ... ?
        """
        self.log(None, '%d children currently running'
                       % (len(self._child_processes)))

    def _poll_children(self):
        """See if children are still running, etc.

        One interesting hook here would be to track memory consumption, etc.
        """
        to_remove = []
        for child_pid, child_path in self._child_processes.iteritems():
            remove_child = True
            try:
                (c_pid, status) = os.waitpid(child_pid, os.WNOHANG)
            except OSError, e:
                trace.warning('Exception while checking child %s status: %s'
                              % (child_pid, e))
            else:
                if c_pid == 0: # Child did not exit
                    remove_child = False
                else:
                    self.log(None, 'child %s exited with status: %s'
                                    % (c_pid, status))
            if remove_child:
                # On error or child exiting, stop tracking the child
                to_remove.append(child_pid)
        for c_id in to_remove:
            # Should we do something about the temporary paths?
            c_path = self._child_processes.pop(c_id)
            if os.path.exists(c_path):
                # The child failed to cleanup after itself, do the work here
                trace.warning('Had to clean up after child %d: %s\n'
                              % (c_id, c_path))
                shutil.rmtree(c_path)

    def _wait_for_children(self):
        start = time.time()
        end = start + self.WAIT_FOR_CHILDREN_TIMEOUT
        while self._child_processes:
            self._poll_children()
            if self.WAIT_FOR_CHILDREN_TIMEOUT > 0 and time.time() > end:
                break
            time.sleep(1.0)
        if self._child_processes:
            trace.warning('Failed to stop children: %s'
                % ', '.join(map(str, self._child_processes)))
            for c_id, c_path in self._child_processes.iteritems():
                if os.path.exists(c_path):
                    trace.warning('Had to clean up after child %d: %s\n'
                                  % (c_id, c_path))
                    shutil.rmtree(c_path)

    def serve_one_connection(self, conn):
        request = conn.recv(1024);
        request = request.strip()
        if request == 'hello':
            self.log(conn, 'hello heartbeat')
            conn.sendall('yep, still alive\n')
            self.log_information()
        elif request == 'quit':
            self._should_terminate = True
            conn.sendall('quit command requested... exiting\n')
            self.log(conn, 'quit requested')
        elif request.startswith('fork '):
            # Not handled yet
            user_id = request[5:]
            self.log(conn, 'fork requested for %r' % (user_id,))
            # TODO: Do we want to limit the number of children?
            self.fork_one_request(conn, user_id)
        else:
            self.log(conn, 'unknown request: %r' % (request,))
        conn.close()


class cmd_launchpad_service(Command):
    """Launch a long-running process, where you can ask for new processes.

    The process will block on a given --port waiting for requests to be made.
    """

    aliases = ['lp-service']

    takes_options = [Option('port',
                        help='Listen for connections on [host:]portnumber',
                        type=str),
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

    def run(self, port=None):
        host, port = self._get_host_and_port(port)
        self._preload_libraries()
        service = LPService(host, port)
        service.main_loop()

register_command(cmd_launchpad_service)


libraries_to_preload = [
    'bzrlib.errors',
    'bzrlib.repository',
    ]
