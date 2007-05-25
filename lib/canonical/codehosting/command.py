import os
import sys
import xmlrpclib

from bzrlib.commands import Command
from bzrlib.option import Option
from bzrlib import urlutils
from bzrlib import ui

from bzrlib.smart import server
from bzrlib.transport import get_transport
from bzrlib.transport.chroot import ChrootServer
from bzrlib.transport.remote import BZR_DEFAULT_PORT, BZR_DEFAULT_INTERFACE

from canonical.config import config
from canonical.codehosting import transport


class cmd_serve(Command):
    """Run the bzr server."""

    aliases = ['server']

    takes_options = [
        Option('port',
               help='listen for connections on nominated port of the form '
                    '[hostname:]portnumber. Passing 0 as the port number will '
                    'result in a dynamically allocated port. Default port is '
                    '4155.',
               type=str),
        ]

    def run(self, port=None):
        authserver = xmlrpclib.ServerProxy(config.codehosting.authserver)
        directory = config.codehosting.branches_root
        user_id = 1 # sabdfl

        lp_server = transport.LaunchpadServer(
            authserver,
            user_id,
            get_transport(urlutils.local_path_to_url(directory)))
        lp_server.setUp()
        t = get_transport(lp_server.get_url())
        host = BZR_DEFAULT_INTERFACE
        if port is None:
            port = BZR_DEFAULT_PORT
        else:
            if ':' in port:
                host, port = port.split(':')
            port = int(port)
        smart_server = server.SmartTCPServer(t, host=host, port=port)
        print 'listening on port: ', smart_server.port
        sys.stdout.flush()
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


if __name__ == '__main__':
    cmd_serve().run()
