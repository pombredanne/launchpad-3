# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bazaar plugin to run the smart server on Launchpad.

Cribbed from bzrlib.builtins.cmd_serve from Bazaar 0.16.
"""

__metaclass__ = type

__all__ = ['cmd_launchpad_server']


import resource
import socket
import sys

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

    def fork_one_request(self, conn, user_id):
        """Fork myself and serve a request."""

    def main_loop(self):
        self._create_master_socket()
        trace.note('Waiting on %s' % (self._sockname,))
        self._should_terminate = False
        while not self._should_terminate:
            try:
                conn, client_addr = self._server_socket.accept()
            except self._socket_timeout:
                # just check if we're asked to stop
                # DEBUG flag to mutter when we get timeouts?
                pass
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
        trace.note('Exiting')

    def log(self, conn, message):
        """Log a message to the trace log.

        Include the information about what connection is being served.
        """
        peer_host, peer_port = conn.getpeername()
        trace.mutter('[%s:%d] %s' % (peer_host, peer_port, message))

    def serve_one_connection(self, conn):
        request = conn.recv(1024);
        request = request.strip()
        if request == 'hello':
            self.log(conn, 'hello heartbeat')
            conn.sendall('yep, still alive\n')
        elif request == 'quit':
            self._should_terminate = True
            conn.sendall('quit command requested... exiting\n')
            self.log(conn, 'quit requested')
        elif request.startswith('fork '):
            # Not handled yet
            user_id = request[5:]
            self.log(conn, 'fork requested for %r' % (user_id,))
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
