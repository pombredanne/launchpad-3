__metaclass__ = type

import xmlrpclib

from canonical.config import config

class BranchStatusError(Exception):
    pass

class BranchStatusClient:

    def __init__(self):
        self.client = xmlrpclib.ServerProxy(
            config.supermirror.authserver_url)

    def getBranchPullQueue(self, branch_type):
        return self.client.getBranchPullQueue(branch_type)

    def startMirroring(self, branch_id):
        assert isinstance(branch_id, int)
        if not self.client.startMirroring(branch_id):
            raise BranchStatusError('startMirroring() failed for branch %d'
                                    % branch_id)

    def mirrorComplete(self, branch_id, last_revision_id):
        assert isinstance(branch_id, int)
        assert (last_revision_id is None or
                isinstance(last_revision_id, basestring)), (
            'last_revision_id must be a string or None')
        if not self.client.mirrorComplete(branch_id, last_revision_id):
            raise BranchStatusError('mirrorComplete() failed for branch %d'
                                    % branch_id)

    def mirrorFailed(self, branch_id, reason):
        assert isinstance(branch_id, int)
        if not self.client.mirrorFailed(branch_id, reason):
            raise BranchStatusError('mirrorFailed() failed for branch %d'
                                    % branch_id)

    def recordSuccess(self, name, hostname, date_started, date_completed):

        # utctimetuple returns a time.struct_t, not a tuple, and xmlrpclib does
        # not know how to marshall this type. So we need to apply tuple() to
        # the return value of utctimetuple() to be able to transmit it.
        started_tuple = tuple(date_started.utctimetuple())
        completed_tuple = tuple(date_completed.utctimetuple())

        if not self.client.recordSuccess(
                name, hostname, started_tuple, completed_tuple):
            raise BranchStatusError('recordSuccess() failed')
