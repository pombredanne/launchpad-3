# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import sys

import bzrlib.branch
from bzrlib.errors import NotBranchError


class BranchToMirror:
    """This class represents a single branch that needs mirroring.

    It has a source URL, a destination URL, a database id and a 
    status client which is used to report on the mirror progress.
    """

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
            dest_branch = bzrlib.bzrdir.BzrDir.open(self.dest).open_branch()
        except bzrlib.errors.NotBranchError:
            os.makedirs(self.dest) 
            dest_branch = bzrlib.bzrdir.BzrDir.create_branch_convenience(
                self.dest, force_new_repo=True, force_new_tree=False,
                #when we update our bzrdir
                # format=srcbranch.bzrdir._format
                )
        try:
            dest_branch.pull(srcbranch, overwrite=True)
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
        return ("<BranchToMirror source=%s dest=%s at %x>" % 
                (self.source, self.dest, id(self)))

