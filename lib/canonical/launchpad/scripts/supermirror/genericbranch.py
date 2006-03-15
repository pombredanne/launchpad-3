import os
import urllib

import lockfile

# XXX The BZR_5_6 branch code needs to be folded into here - jblack
# 2006-05-13
class GenericBranch:
    """The prototypical supermirror representation of a branch."""

    supported_formats = ["A non existant detection file\n"]
    version_file = ".bzr/branch-format"
    branchtype = "generic"
    lock = None
    
    def __init__(self, src=None, dest=None):
        self.source = src
        self.dest = dest

    def run(self):
        self.mirror()

    # XXX generic branches are intended to be abstract. As such, they are
    # never, ever equal as they should never be instantiated. Well, that is
    # until after BZR_5_6 gets folded in, which has the __eq__ method that
    # we'll need to use - jblack 2005-03-13
    def __eq__(self, twin):
        raise NotImplementedError

    def __repr__(self):
        return ("branch <type=%s source=%s dest=%s at %x>" % 
                (self.branchtype, self.source, self.dest, id(self)))

    def finished (self, requireLock=True):
        """Release lock on branch when done
        
        @param: requireLock - if set, this method will raise a runTimeError
        if one marks a branch as finished without unlocking.
        """
        #XXX This code is here for when we eventually need to lock on a
        # branch basis rather than a script wide basis. However, its not
        # being used quite yet, but since its already written... -jblack
        # 2006-03-13
        raise NotImplementedError
        if self.lock is None:
            if requireLock == True:
                raise RuntimeError
        else:
            self.lock.release()

    def sortidentity(self):
        # XXX Untested code. needs test case first. -jblack 2005-05-13
        raise NotImplementedError

        if source.find(":") < 0:
            return "localhost"

        source = source[source.find(":")+1:]
        source = self.src.tolower()
        hostport = urllib.splithost(source)[0]
        host = urllib.splitport(hostport)[0]
        return host

    def mirror(self):
        try:
            self._mirror()
        except Exception, e:
            print 
            print "@BZR_ERROR_START@"
            print "@BZR_ERROR_MSG@ Unknown error"
            print "@BZR_ERROR_SRC@ %s" % self.source
            print "@BZR_ERROR_DEST@ %s" % self.dest
            print "@BZR_ERROR_TRACEBACK_START@"
            print e.__class__ 
            print "@BZR_ERROR_TRACEBACK_END@"
            print "@BZR_ERROR_END@"
            print "\n"

    # XXX When BZR_5_6 gets folded in, this will be folded into mirror.
    # -jblack 2006-03-13
    def _mirror(self):
        """This is an abstract method as a genericbranch is not
        mirrorable"""
        raise NotImplementedError
           
    def supportsFormat(self, url=None):
        """Does this branch class support this branch format

        @param: url - an optional location to check.
        """
        if url is None:
            url = self.source
        if url[-1] == "/":
            file = url + self.version_file
        else:
            file = url + "/" + self.version_file

        try:
            data = urllib.urlopen(file).readline()
        except IOError:
            return False

        for x in self.supported_formats:
            if x == data:
                return True
        return False
        
