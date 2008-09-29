#!/usr/bin/python2.4
""" Copyright Canonical Limited 2005
 Author: Daniel Silverstone <daniel.silverstone@canonical.com>
         Celso Providelo <celso.providelo@canonical.com>

Buildd-Slave monitor, support multiple slaves and requires LPDB access.
"""
import urlparse
import _pythonpath

from string import join
from sqlobject import SQLObjectNotFound

from canonical.lp import initZopeless
from canonical.config import config
from canonical.launchpad.database import Builder
from canonical.launchpad.scripts import execute_zcml_for_scripts

from twisted.internet import stdio
from twisted.protocols import basic
from twisted.internet import reactor, defer
from twisted.web.xmlrpc import Proxy

class BuilddSlaveMonitorApp:
    """Simple application class to expose some special methods and
    wrap to the RPC server.
    """
    def __init__(self, tm, write):
        self.tm = tm
        self.write = write

    def requestReceived(self, line):
        """Process requests typed in."""
        # identify empty ones
        if line.strip() == '':
            self.prompt()
            return
        request = line.strip().split()

        # select between local or remote method
        cmd = 'cmd_' + request[0]

        if hasattr(self, cmd):
            args = request[1:]
            meth = getattr(self, cmd)
            d = defer.maybeDeferred(meth, args)
            d.addCallbacks(self._printResult).addErrback(self._printError)
            return

        elif len(request) > 1:
            try:
                builder_id = request.pop(1)
                bid = int(builder_id)
                builder = Builder.get(bid)
            except ValueError:
                self.write('Wrong builder ID: %s' % builder_id)
            except SQLObjectNotFound:
                self.write('Builder Not Found: %s' % bid)
            else:
                urlbase = builder.url.encode('ascii')
                rpcurl = urlparse.urljoin(urlbase, '/rpc/')
                slave = Proxy(rpcurl)
                d = slave.callRemote(*request)
                d.addCallbacks(self._printResult).addErrback(self._printError)
                return
        else:
            self.write('Syntax Error: %s' % request)

        self.prompt()
        return

    def prompt(self):
        """Simple display a prompt according with current state."""
        self.write('\nbuildd-monitor>>> ')

    def cmd_quit(self, args):
        """Ohh my ! stops the reactor, i.e., QUIT, if requested."""
        reactor.stop()

    def cmd_builders(self, args):
        """Read access through initZopeless."""
        builders = Builder.select(orderBy='id')
        blist = 'List of Builders\nID - STATUS - NAME - URL\n'
        for builder in builders:
            name = builder.name.encode('ascii')
            url = builder.url.encode('ascii')
            blist += '%s - %s - %s - %s\n' % (builder.id, builder.builderok,
                                              name, url)
        return blist

    def cmd_reset(self, args):
        if len(args) < 1:
            return 'A builder ID was not supplied'

        try:
            build_id = int(args[0])
        except ValueError:
            return 'Argument must be the builder ID'

        try:
            builder = Builder.get(build_id)
        except SQLObjectNotFound:
            return 'Builder not found: %d' % int(args[0])

        builder.builderok = True
        self.tm.commit()

        return '%s was reset sucessfully' % builder.name

    def cmd_clear(self, args):
        """Simply returns the VT100 reset string."""
        return '\033c'

    def cmd_help(self, args):
        return ('Command Help\n'
                'clear - clear screen'
                'builders - list available builders\n'
                'reset <BUILDERID> - reset builder\n'
                'quit - exit the program\n'
                'Usage: <CMD> <BUILDERID> <ARGS>\n')

    def _printResult(self, result):
        """Callback for connections."""
        if result is None:
            return
        self.write('Got: %s' % str(result).strip())
        self.prompt()

    def _printError(self, error):
        """ErrBack for normal RPC transactions."""
        self.write('Error: ' + repr(error))
        self.prompt()

class BuilddSlaveMonitorProtocol(basic.LineReceiver):
    """Terminal Style Protocol"""
    # set local line delimiter
    from os import linesep as delimiter
    # store the trasaction manager locally
    tm = None

    def connectionMade(self):
        """Setup the backend application and send welcome message."""
        self.app = BuilddSlaveMonitorApp(self.tm, self.transport.write)
        self.transport.write('Welcome Buildd Slave Monitor\n>>> ')

    def lineReceived(self, line):
        """Use the Backend App to process each request."""
        self.app.requestReceived(line)

def main(tm):
    """Setup the interactive interface with the respective protocol,
    and start the reactor.
    """
    # ensure we store the transaction manager instance before
    # initialise the reactor.
    proto = BuilddSlaveMonitorProtocol()
    proto.tm = tm
    stdio.StandardIO(proto)
    reactor.run()

if __name__ == '__main__':
    # for main, the only think to setup is the initZopeless
    # environment and the application wrapper.
    execute_zcml_for_scripts()
    tm = initZopeless(dbuser=config.builddmaster.dbuser)
    main(tm)
