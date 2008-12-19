"""Implementation of the dynamic RewriteMap used to serve branches over HTTP.
"""

import time
import xmlrpclib

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.branchfsclient import BranchFileSystemClient
from canonical.config import config
from canonical.launchpad.ftests import ANONYMOUS
from canonical.launchpad.interfaces.codehosting import BRANCH_TRANSPORT
from canonical.launchpad.xmlrpc import faults
from canonical.twistedsupport import extract_result

__all__ = ['BranchRewriter']

class BranchRewriter:

    def __init__(self, logger, proxy):
        self.logger = logger
        self.client = BranchFileSystemClient(proxy, ANONYMOUS, 1.0)

    def rewriteLine(self, resource_location):
        """Rewrite 'resource_location' to a more concrete location.

        We use the 'translatePath' BranchFileSystemClient method.  There are
        three cases:

         (1) The request is for something within the .bzr directory of a
             branch.

             In this case we rewrite the request to the location from which
             branches are served by ID.

         (2) The request is for something within a branch, but not the .bzr
             directory.

             In this case, we hand the request off to codebrowse.

         (3) The branch is not found.  Two sub-cases: the request is for a
             product control directory or the we don't know how to translate
             the path.

             In both these cases we return 'NULL' which indicates to Apache
             that we don't know how to rewrite the request (and so it should
             go on to generate a 404 response).

        Other errors are allowed to propagate, on the assumption that the
        caller will catch and log them.
        """
        T = time.time()
        trailingSlash = resource_location.endswith('/')
        deferred = self.client.translatePath(resource_location)
        try:
            transport_type, info, trailing = extract_result(deferred)
        except xmlrpclib.Fault, f:
            if f.faultCode == faults.PathTranslationError.error_code:
                return "NULL"
            else:
                raise
        if transport_type == BRANCH_TRANSPORT:
            if trailing.startswith('.bzr'):
                r = ('http://bazaar-internal.launchpad.dev/' +
                     branch_id_to_path(info['id']) + '/' + trailing)
                if trailingSlash:
                    r += '/'
            else:
                r = (config.codehosting.internal_codebrowse_root +
                     resource_location)
            self.logger.info("%r -> %r (%fs)", resource_location, r, time.time() - T)
            return r
        else:
            return "NULL"
