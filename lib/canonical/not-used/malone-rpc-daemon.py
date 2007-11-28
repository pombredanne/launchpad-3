#!/usr/bin/python2.4
"""XML-RPC server for Malone in Twisted.

To run the server, just run this file ("rpcdaemon.py").

"""

from twisted.web import xmlrpc
import sqlobject, optparse

from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.database import Bug
from canonical.lp import initZopeless

class OptionHelpException(optparse.OptParseError):
    """
    Raised in order to pass help back to the client without exiting the
    program.
    """

class MyOptionParser(optparse.OptionParser):
    """
    Subclass OptionParser so we can return the output to the client instead of
    printing it to the console on the server
    """

    def error (self, msg):
        """error(msg : string)

        Print a usage message incorporating 'msg' to stderr and exit.
        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        raise OptionHelpException("%s: error: %s\n%s" % (self._get_prog_name(),
            msg, self.get_usage()))

    def print_usage (self, file=None):
        """print_usage(file : file = stdout)

        Print the usage message for the current program (self.usage).
        Any occurence of the string "%prog" in
        self.usage is replaced with the name of the current program
        (basename of sys.argv[0]).  Does nothing if self.usage is empty
        or not defined.
        """
        raise OptionHelpException(self.get_usage())

    def print_version (self, file=None):
        """print_version(file : file = stdout)

        Print the version message for this program (self.version).
        As with print_usage(), any occurence of "%prog" in
        self.version is replaced by the current program's name.
        Does nothing if self.version is empty or undefined.
        """
        raise OptionHelpException(self.get_version())

    def print_help (self, file=None):
        """print_help(file : file = stdout)

        Print an extended help message, listing all options and any
        help text provided with them.
        """
        raise OptionHelpException(self.format_help())

# end class MyOptionParser

class RPCDaemon(xmlrpc.XMLRPC):
    """XMLRPC daemon handler.
    
    """
    
    def __init__(self):
        xmlrpc.XMLRPC.__init__(self)
        initZopeless()
        self.debug=1

    def xmlrpc_runcommand(self, cmd, locale, packedargs):
        """Run a command."""
        if self.debug:
            print ">>> runcommand called with cmd=%s, locale=%s, args=%s" % (
                cmd, locale, packedargs)
        if len(packedargs) != 2:
            if self.debug:
                print "<<< *** Invalid argument format"
            raise xmlrpc.Fault(-32000,"Invalid Argument Format")
        cmd = cmd.lower().replace("-", "_")
        options = packedargs[0]
        args = packedargs[1]
        # At this point, the user's authentication info will be in the
        # options dictionary.  Once we care about auth, process it here.
        try:
            cmdmethod = getattr(self, "cmd_" + cmd);
        except AttributeError:
            if self.debug:
                print "<<< *** Command not implemented"
            raise xmlrpc.Fault(-32601,"Command not implemented")
        # if we made it here, it exists. Call it.
        try:
            result = cmdmethod(args)
        except OptionHelpException, val:
            result = ("error", val)
        except ValueError, val:
            result = ("error", val)
        if self.debug:
            print "<<< returning with result = %s" % (result,)
        return result

    def serialize_assignments(self, bug):
        newlist = []
        for a in bug.sourceassignment:
            newlist.append({
                'product': a.product,
                'status': a.status,
                'severity': a.severity,
                })
        return newlist

    def serialize_bug(self, bug):
        data = {
            'id': bug.id,
            'datecreated': str(bug.datecreated),
            'title': bug.title,
            'description': bug.description,
            #'productassignment': list(bug.productassignment()),
            'sourceassignment': self.serialize_assignments(bug),
            #'duplicateof': bug.duplicateof,
            }
        return data

    def serialize_buglist(self, buglist):
        newbuglist = []
        for bug in buglist:
            newbuglist.append(self.serialize_bug(bug))
        return newbuglist

    # Command definitions

    # Add any new commands below this point.  They'll automatically be found
    # if you create them.  Method name is "cmd_" followed by the command the
    # end user will type, with any hyphens replaced by underscores.

    def cmd_get_field(self, args):
        parser = MyOptionParser(prog="get-field",
            usage="%prog FIELD BUG-ID")
        (opts,args) = parser.parse_args(args)
        if len(args) < 2:
            parser.error("Not enough arguments")
        if len(args) > 2:
            parser.error("Too many arguments")
        field = args[0]
        if not args[1].isdigit():
            parser.error("The bug ID must be a number")
        id = int(args[1])
        if self.debug:
            print "--- id = %d" % id
        try:
            bug = Bug.get(id)
        except sqlobject.main.SQLObjectNotFound:
            return ("error", "Bug not found")
        try:
            result = getattr(bug,field)
        except AttributeError:
            return ("error", "Field not found")
        return ("result", result)

    def cmd_show(self, args):
        parser = MyOptionParser(usage="%prog BUG-ID", prog="show")
        (opts,args) = parser.parse_args(args)
        if len(args) < 1:
            parser.error("Not enough arguments")
        if len(args) > 1:
            parser.error("Too many arguments")
        if not args[0].isdigit():
            parser.error("The bug ID must be a number")
        return self.cmd_list_bugs(["--id",args[0]])

    def cmd_list_bugs(self, args):
        parser = MyOptionParser(prog="list-bugs",
            usage="%prog [options]")
        parser.add_option("--id", type="int", help="the bug ID")
        parser.add_option("--title", type="string", help="the bug title")
        (options,args) = parser.parse_args(args)
        if len(args) > 0:
            parser.error("Too many arguments")
        fieldlist = []
        for option in ("id","title"):
            if getattr(options, option):
                fieldlist.insert(-1,option)
        if len(fieldlist) < 1:
            parser.error("You must supply at least one search option")
        andlist = []
        for field in fieldlist:
            andlist.insert(-1,"lower(%s) like %s" %
                # lower(title) like '%foo%'
                (field, quote("%%%s%%" % getattr(options, field)))
                )
        wherepart = "(" + ") AND (".join(andlist) + ")"
        try:
            buglist = list(Bug.select(wherepart))
        except sqlobject.main.SQLObjectNotFound:
            return ("error", "No bugs found")
        return ("result", self.serialize_buglist(buglist))

        # end command definitions

# end class RPCDaemon

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
