"""Implementation of the dynamic RewriteMap used to serve branches over HTTP.
"""

import time

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.branchfsclient import BranchFileSystemClient
from canonical.config import config
from canonical.launchpad.ftests import ANONYMOUS
from canonical.launchpad.interfaces.codehosting import (
    BRANCH_TRANSPORT)
from canonical.twistedsupport import extract_result

__all__ = ['BranchRewriter']

class BranchRewriter:

    def __init__(self, logger, proxy):
        self.logger = logger
        self.client = BranchFileSystemClient(proxy, ANONYMOUS, 1.0)

    def rewriteLine(self, line):
        """XXX.

        XXX.
        """
        T = time.time()
        trailingSlash = line.endswith('/')
        deferred = self.client.translatePath(line)
        transport_type, info, trailing = extract_result(deferred)
        if transport_type == BRANCH_TRANSPORT:
            if trailing.startswith('.bzr'):
                r = '/' + branch_id_to_path(info['id']) + '/' + trailing
                if trailingSlash:
                    r += '/'
            else:
                r = config.codehosting.internal_codebrowse_root + line
            self.logger.info("%r -> %r (%fs)", line, r, time.time() - T)
            return r
        else:
            return "NULL"
