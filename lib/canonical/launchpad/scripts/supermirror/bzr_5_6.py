# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import sys

import bzrlib.branch
from bzrlib.errors import NotBranchError

from canonical.launchpad.scripts.supermirror.genericbranch import GenericBranch


# XXX This needs to be folded into genericbranch. Some of the stuff,
# such as supported_formats, won't be necessary any more. -jblack
# 2006-05-13
class BZR_5_6(GenericBranch):

    supported_formats = ["Bazaar-NG branch, format 6\n",
                         "Bazaar-NG branch, format 5\n"]
    version_file = ".bzr/branch-format"
    branchtype = "bzr_5_6"

    def _mirror(self):
        if self.dest is None:
            raise RuntimeError,"No destination for mirror"
        if self.source is None:
            raise RuntimeError,"No source for source"
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

    def deleteMirror(self):
        raise NotImplementedError

    # XXX BIG FAT WARNING
    # after this gets folded into GenericBranch, you'll have to test not
    # just revision_history, but the branch format as well. This is because
    # a person can do an upgrade for a branch, which won't change the
    # revision history. - jblack 2005-03-13
    def __eq__(self, twin):
        srcbranch = bzrlib.branch.Branch.open(self.source)
        destbranch = bzrlib.branch.Branch.open(twin.source)
        return srcbranch.revision_history() == destbranch.revision_history()

