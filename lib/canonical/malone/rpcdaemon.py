#!/usr/bin/env python
"""XML-RPC server for Malone in Twisted.

To run the server, just run this file ("rpcdaemon.py").

"""

#from twisted.manhole import gladereactor
#gladereactor.install()

from twisted.web import xmlrpc
from sqlobject import connectionForURI
from canonical.arch.sqlbase import SQLBase, quote
from canonical.database.malone import Bug
import xmlrpclib, sqlobject

class RPCDaemon(xmlrpc.XMLRPC):
    """XMLRPC daemon handler.
    
    """
    
    def __init__(self):
	xmlrpc.XMLRPC.__init__(self)
        SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))
	self.debug=1

    def xmlrpc_runcommand(self, cmd, locale, packedargs):
        """Run a command."""
	if self.debug:
            print ">>> runcommand called with cmd=%s, locale=%s, args=%s" % (cmd,
                locale, packedargs)
        if len(packedargs) != 2:
            if self.debug:
                print "<<< *** Invalid argument format"
            raise xmlrpc.Fault(-32000,"Invalid Argument Format")
        cmd = cmd.lower().replace("-", "_")
        options = packedargs[0]
        args = packedargs[1]
        try:
            cmdmethod = getattr(self, "cmd_" + cmd);
        except AttributeError:
            if self.debug:
                print "<<< *** Command not implemented"
            raise xmlrpc.Fault(-32601,"Command not implemented")
        # if we made it here, it exists. Call it.
        result = cmdmethod(args)
        if self.debug:
            print "<<< returning with result = %s" % result
        return result

    def serialize_bug(self, bug):
        data = {
            'id': bug.id,
            'datecreated': str(bug.datecreated),
            'title': bug.title,
            'description': bug.description,
            'duplicateof': bug.duplicateof,
        }
        return data

    def serialize_buglist(self, buglist):
        newbuglist = []
        for bug in buglist:
            newbuglist.append(self.serialize_bug(bug))
        return newbuglist

    def cmd_get_field(self, args):
        if len(args) < 2:
            return ["error", "Not enough arguments"]
        if len(args) > 2:
            return ["error", "Too many arguments"]
        field = args[0]
        if not args[1].isdigit():
            return ["error", "The bug ID must be a number"]
        id = int(args[1])
        try:
            bug = Bug.get(id)
        except sqlobject.main.SQLObjectNotFound:
            return ["error", "Bug not found"]
        try:
            result = getattr(bug,field)
        except AttributeError:
            return ["error", "Field not found"]
	return ["result", result]

    def cmd_show(self, args):
        if len(args) < 1:
            return ["error", "Too few arguments"]
        if len(args) > 1:
            return ["error", "Too many arguments"]
        if not args[0].isdigit():
            return ["error", "The bug ID must be a number"]
        return self.cmd_list_bugs(["id",args[0]])

    def cmd_list_bugs(self, args):
        #if len(args) > 0:
        #    return ["error", "Too many arguments"]
        #id = int(args[0])
        field = args[0]
        search = args[1]
        try:
            buglist = list(Bug.select("lower(%s) like %s" %
                # lower(title) like '%foo%'
                (field, quote("%%%s%%" % args[0].lower() ))
                ))
        except sqlobject.main.SQLObjectNotFound:
            return ["error", "No bugs found"]
	return ["result", self.serialize_buglist(buglist)]

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
