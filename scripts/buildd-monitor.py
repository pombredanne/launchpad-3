#!/usr/bin/env python
""" Copyright Canonical Limited 2005
 Author: Daniel Silverstone <daniel.silverstone@canonical.com>
         Celso Providelo <celso.providelo@canonical.com>

Buildd-Slave monitor, support multiple slaves and requires LPDB access.
"""
from string import join

from canonical.lp import initZopeless
from canonical.launchpad.database import Builder

from twisted.internet import stdio
from twisted.protocols import basic
from twisted.internet import reactor, defer
from twisted.web.xmlrpc import Proxy

class BuilddSlaveMonitorApp:
    """Simple application class to expose some special methods and
    wrap to the RPC server.
    """
    def __init__(self, write):
        self.write = write
        self.slave = None

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
            args = join(request[1:])
            meth = getattr(self, cmd)
            d = defer.maybeDeferred(meth, args)
        else:
            if not self.slave:
                self.write('No Buildd Slave selected\n')
                self.prompt()
                return
            d = self.slave.callRemote(*request)

        d.addCallbacks(self._printResult).addErrback(self._printError)
    
    def prompt(self):
        """Simple display a prompt according with current state."""
        if self.slave:
            self.write('\n%s >>> ' % self.builder.name.encode('ascii'))
        else:
            self.write('\n>>> ')
            
    def cmd_quit(self, data=None):
        """Ohh my ! stops the reactor, i.e., QUIT, if requested.""" 
        reactor.stop()

    def cmd_builders(self, data=None):
        """Read access through initZopeless."""
        builders = Builder.select()
        for builder in builders:
            name = builder.name.encode('ascii')
            url = builder.url.encode('ascii')
            return ('%s - %s - %s\n' % (builder.id, name, url))
        
    def cmd_connect(self, data=None):
        """Select an slave to be monitored."""
        if data:
            self.builder = Builder.get(int(data))
            self.url = self.builder.url.encode('ascii')

        self.slave = Proxy(self.url)
        return 'Connected to %s\n' % self.builder.name.encode('ascii')

    def cmd_disconnect(self, data=None):
        """Release the slave."""
        self.slave = None
            
    def _printResult(self, result):
        """Callback for connections."""
        if result is None:
            return
        self.write('Got: ' + repr(result))
        self.prompt()
            
    def _printError(self, error):
        """ErrBack for normal RPC transactions."""
        self.write('Error: ' + repr(error))
        self.prompt()

class BuilddSlaveMonitorProtocol(basic.LineReceiver):
    """Terminal Style Protocol"""
    # set local line delimiter
    from os import linesep as delimiter

    def connectionMade(self):
        """Setup the backend application and send welcome message."""
        self.app = BuilddSlaveMonitorApp(self.transport.write)
        self.transport.write('Welcome Buildd Slave Monitor\n>>> ')

    def lineReceived(self, line):
        """Use the Backend App to process each request."""
        self.app.requestReceived(line)

def main():
    """Setup the interactive interface with the respective protocol,
    and start the reactor.
    """
    stdio.StandardIO(BuilddSlaveMonitorProtocol())
    reactor.run()
    
if __name__ == '__main__':
    # for main, the only think to setup is the initZopeless
    # environment and the application wrapper. 
    initZopeless()
    main()
