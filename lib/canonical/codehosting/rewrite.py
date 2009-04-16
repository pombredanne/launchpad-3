"""Implementation of the dynamic RewriteMap used to serve branches over HTTP.
"""

import time
import xmlrpclib

from bzrlib import urlutils

from canonical.codehosting.vfs import (
    branch_id_to_path, BranchFileSystemClient)
from canonical.config import config
from lp.code.interfaces.codehosting import (
    BRANCH_TRANSPORT, LAUNCHPAD_ANONYMOUS)
from canonical.launchpad.xmlrpc import faults
from canonical.twistedsupport import extract_result

__all__ = ['BranchRewriter']


class BranchRewriter:

    def __init__(self, logger, proxy):
        """

        :param logger: Logger than messages about what the rewriter is doing
            will be sent to.
        :param proxy: A blocking proxy for a branchfilesystem endpoint.
        """
        self.logger = logger
        self.client = BranchFileSystemClient(proxy, LAUNCHPAD_ANONYMOUS, 1.0)

    def _codebrowse_url(self, path):
        return urlutils.join(
            config.codehosting.internal_codebrowse_root,
            path)

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
        # Codebrowse generates references to its images and stylesheets
        # starting with "/static", so pass them on unthinkingly.
        if resource_location.startswith('/static/'):
            return self._codebrowse_url(resource_location)
        trailingSlash = resource_location.endswith('/')
        deferred = self.client.translatePath(resource_location)
        try:
            transport_type, info, trailing = extract_result(deferred)
        except xmlrpclib.Fault, f:
            if faults.check_fault(f, faults.PathTranslationError):
                return "NULL"
            elif faults.check_fault(f, faults.PermissionDenied):
                # If we get permission denied, send to codebrowse which will
                # redirect to the https version of the codehost, which doesn't
                # indirect through here and does authentication via OpenID.
                # If we could generate a 30x response to the client from here,
                # we'd do it, but we can't.
                return self._codebrowse_url(resource_location)
            else:
                raise
        if transport_type == BRANCH_TRANSPORT:
            if trailing.startswith('.bzr'):
                r = urlutils.join(
                    config.codehosting.internal_branch_by_id_root,
                    branch_id_to_path(info['id']), trailing)
                if trailingSlash:
                    r += '/'
            else:
                r = self._codebrowse_url(resource_location)
            self.logger.info(
                "%r -> %r (%fs)", resource_location, r, time.time() - T)
            return r
        else:
            return "NULL"
