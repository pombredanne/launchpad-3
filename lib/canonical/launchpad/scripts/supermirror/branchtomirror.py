# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import sys

import bzrlib.branch
from bzrlib.errors import NotBranchError


class BranchToMirror:

    def __init__(self, src, dest):
        self.source = src
        self.dest = dest
        assert self.dest is not None
        assert self.source is not None

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

    def _mirror(self):
        try: 
            srcbranch = bzrlib.branch.Branch.open(self.source)
        except bzrlib.errors.NotBranchError:
            print >> sys.stderr,  "%s is unreachable" % (self.source)
            return
        try:
            destdir = bzrlib.bzrdir.BzrDir.open(self.dest)
            #destbranch = bzrlib.branch.Branch.open(self.dest)
            destdir.open_branch().pull(srcbranch, overwrite=True)
        except NotBranchError:
            os.makedirs(self.dest) 
            destdir = srcbranch.bzrdir.clone(self.dest)

    def __eq__(self, other):
        return self.source == other.source and self.dest == other.dest

    def __repr__(self):
        return ("BranchToMirror <source=%s dest=%s at %x>" % 
                (self.source, self.dest, id(self)))

