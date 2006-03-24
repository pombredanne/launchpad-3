# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import sys

import bzrlib.branch
from bzrlib.errors import NotBranchError


class BranchToMirror:

    def __init__(self, src, dest, branch_status_client, branch_id):
        self.source = src
        self.dest = dest
        self.branch_status_client = branch_status_client
        self.branch_id = branch_id
        assert self.dest is not None
        assert self.source is not None

    def mirror(self):
        self.branch_status_client.startMirroring(self.branch_id)
        try: 
            srcbranch = bzrlib.branch.Branch.open(self.source)
        except bzrlib.errors.BzrError, e:
            self.branch_status_client.mirrorFailed(self.branch_id, str(e))
            return
        try:
            destdir = bzrlib.bzrdir.BzrDir.open(self.dest)
            destdir.open_branch().pull(srcbranch, overwrite=True)
        except bzrlib.errors.NotBranchError:
            os.makedirs(self.dest) 
            destdir = srcbranch.bzrdir.clone(self.dest)
        # add further encountered errors from the production runs here
        # ------ HERE ---------
        #
        except bzrlib.errors.BzrError:
            self.branch_status_client.mirrorFailed(self.branch_id, str(e))
            return
        self.branch_status_client.mirrorComplete(self.branch_id)

    def __eq__(self, other):
        return self.source == other.source and self.dest == other.dest

    def __repr__(self):
        return ("BranchToMirror <source=%s dest=%s at %x>" % 
                (self.source, self.dest, id(self)))

