#!/usr/bin/env python
"""XML-RPC server for Malone in Twisted.

To run the server, just run this file ("rpcdaemon.py").

"""

#from twisted.manhole import gladereactor
#gladereactor.install()

from twisted.web import xmlrpc
from sqlobject import connectionForURI
from canonical.arch.sqlbase import SQLBase
from canonical.malone.sql import Bug
import xmlrpclib

class RPCDaemon(xmlrpc.XMLRPC):
    """XMLRPC daemon handler.
    
    """
    
    def __init__(self):
	xmlrpc.XMLRPC.__init__(self)
        SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))
	self.debug=1

    def xmlrpc_getBugField(self,field,id):
        """Get bug title."""
	if self.debug:
	  print "getBugField(field='%s',id=%s) called" % (field, id)
        id = int(id)
        bug = Bug.get(id)
	return getattr(bug,field)

def main():
    from twisted.internet import reactor
    from twisted.web import server

    port = 8090
    r = RPCDaemon()
    if r.debug:
        print "RPC Daemon running on port %d" % port
    reactor.listenTCP(port, server.Site(r))
    reactor.run()


if __name__ == '__main__':
    main()

# arch-tag: fc5ed49f-b515-440c-8fdb-ae38ce3b8a7f
