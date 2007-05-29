# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Bazaar plugin to run the smart server on Launchpad.

Cribbed from bzrlib.builtins.cmd_serve from Bazaar 0.16.
"""

__metaclass__ = type

__all__ = ['cmd_launchpad_server']


import sys
import xmlrpclib

from bzrlib.commands import Command, register_command
from bzrlib.option import Option
from bzrlib import urlutils, ui

from bzrlib.smart import medium, server
from bzrlib.transport import get_transport
from bzrlib.transport import remote

from canonical.config import config
from canonical.codehosting import transport


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
                    '[hostname:]portnumber. Passing 0 as the port number will '
                    'result in a dynamically allocated port. Default port is '
                    '4155.',
               type=str),
        Option('directory',
               help='serve contents of directory. Defaults to '
                    'config.codehosting.branches_root.',
               type=unicode),
        Option('authserver_url',
               help='the url of the internal XML-RPC server. Defaults to '
                    'config.codehosting.authserver.',
               type=unicode),
        Option('read-only',
               help='By default the server is a read/write server. Supplying '
                    '--read-only disables write access to the contents of '
                    'the served directory and below. '
                ),
        ]

    takes_args = ['user_id']

    def get_transport(self, authserver, user_id, url):
        lp_server = transport.LaunchpadServer(
            authserver,
            user_id,
            get_transport(url))
        lp_server.setUp()
        return get_transport(lp_server.get_url())

    def get_smart_server(self, transport, port, inet):
        if inet:
            smart_server = medium.SmartServerPipeStreamMedium(
                sys.stdin, sys.stdout, transport)
        else:
            host = remote.BZR_DEFAULT_INTERFACE
            if port is None:
                port = remote.BZR_DEFAULT_PORT
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
        # for the duration of this server, no UI output is permitted.
        # note that this may cause problems with blackbox tests. This should
        # be changed with care though, as we dont want to use bandwidth sending
        # progress over stderr to smart server clients!
        old_factory = ui.ui_factory
        try:
            ui.ui_factory = ui.SilentUIFactory()
            smart_server.serve()
        finally:
            ui.ui_factory = old_factory

    def run(self, user_id, port=None, directory=None, read_only=False,
            authserver_url=None, inet=False):
        if directory is None:
            directory = config.codehosting.branches_root
        if authserver_url is None:
            authserver_url = config.codehosting.authserver

        url = urlutils.local_path_to_url(directory)
        if read_only:
            url = 'readonly+' + url
        authserver = xmlrpclib.ServerProxy(authserver_url)

        transport = self.get_transport(authserver, user_id, url)
        smart_server = self.get_smart_server(transport, port, inet)
        self.run_server(smart_server)


register_command(cmd_launchpad_server)
