# Copyright 2006 Canonical Ltd.  All rights reserved.

import logging
import os
import socket
import traceback

import bzrlib.branch
import bzrlib.errors


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
        self._source_branch = None
        self._dest_branch = None
        assert self.dest is not None
        assert self.source is not None

    def _openSourceBranch(self):
        """Open the branch to pull from, useful to override in tests."""
        self._source_branch = bzrlib.branch.Branch.open(self.source)

    def _openDestBranch(self):
        """Open the branch to pull to, creating a new one if necessary.
        
        Useful to override in tests.
        """
        try:
            branch = bzrlib.bzrdir.BzrDir.open(self.dest).open_branch()
        except bzrlib.errors.NotBranchError:
            os.makedirs(self.dest) 
            branch = bzrlib.bzrdir.BzrDir.create_branch_convenience(
                self.dest, force_new_repo=True, force_new_tree=False,
                #when we update our bzrdir
                # format=srcbranch.bzrdir._format
                )
        self._dest_branch = branch

    def _pullSourceToDest(self):
        """Pull the contents of self._source_branch into self._dest_branch."""
        assert self._source_branch is not None
        assert self._dest_branch is not None
        self._dest_branch.pull(self._source_branch, overwrite=True)

    def _mirrorFailed(self, error):
        self.branch_status_client.mirrorFailed(self.branch_id, str(error))

    def mirror(self):
        logger = logging.getLogger('supermirror-pull')
        self.branch_status_client.startMirroring(self.branch_id)
        try: 
            self._openSourceBranch()
        # XXX: We catch socket.error here to prevent bzrlib regressions/bugs
        # to break the supermirror-puller. In case we catch a socket.error
        # we'll log it so kiko nag mbp to fix them in bzrlib.
        # Guilherme Salgado, 2006-04-24
        except (socket.error, bzrlib.errors.BzrError), e:
            if isinstance(e, socket.error):
                logger.warn(
                    'Possible bug found in bzrlib:\n%s' % traceback.print_exc())
            self._mirrorFailed(e)
            return

        self._openDestBranch()

        try:
            self._pullSourceToDest()
        # add further encountered errors from the production runs here
        # ------ HERE ---------
        #
        # XXX: We catch socket.error here to prevent bzrlib regressions/bugs
        # to break the supermirror-puller. In case we catch a socket.error
        # we'll log it so kiko nag mbp to fix them in bzrlib.
        # Guilherme Salgado, 2006-04-24
        except (socket.error, bzrlib.errors.BzrError), e:
            if isinstance(e, socket.error):
                logger.warn(
                    'Possible bug found in bzrlib:\n%s' % traceback.print_exc())
            self._mirrorFailed(e)
            return

        self.branch_status_client.mirrorComplete(self.branch_id)

    def __eq__(self, other):
        return self.source == other.source and self.dest == other.dest

    def __repr__(self):
        return ("<BranchToMirror source=%s dest=%s at %x>" % 
                (self.source, self.dest, id(self)))

