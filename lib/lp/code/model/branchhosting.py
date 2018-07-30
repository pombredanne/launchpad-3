# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Communication with the Loggerhead API for Bazaar code hosting."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BranchHostingClient',
    ]

import json
import sys

from lazr.restful.utils import get_current_browser_request
import requests
from six import reraise
from six.moves.urllib_parse import (
    quote,
    urljoin,
    )
from zope.interface import implementer

from lp.code.errors import (
    BranchFileNotFound,
    BranchHostingFault,
    )
from lp.code.interfaces.branchhosting import IBranchHostingClient
from lp.code.interfaces.codehosting import BRANCH_ID_ALIAS_PREFIX
from lp.services.config import config
from lp.services.timeline.requesttimeline import get_request_timeline
from lp.services.timeout import (
    get_default_timeout_function,
    TimeoutError,
    urlfetch,
    )


class RequestExceptionWrapper(requests.RequestException):
    """A non-requests exception that occurred during a request."""


@implementer(IBranchHostingClient)
class BranchHostingClient:
    """A client for the Bazaar Loggerhead API."""

    def __init__(self):
        self.endpoint = config.codehosting.internal_bzr_api_endpoint

    def _request(self, method, branch_id, quoted_tail, as_json=False,
                 **kwargs):
        """Make a request to the Loggerhead API."""
        # Fetch the current timeout before starting the timeline action,
        # since making a database query inside this action will result in an
        # OverlappingActionError.
        get_default_timeout_function()()
        timeline = get_request_timeline(get_current_browser_request())
        components = [BRANCH_ID_ALIAS_PREFIX, str(branch_id)]
        if as_json:
            components.append("+json")
        components.append(quoted_tail)
        path = "/" + "/".join(components)
        action = timeline.start(
            "branch-hosting-%s" % method, "%s %s" % (path, json.dumps(kwargs)))
        try:
            response = urlfetch(
                urljoin(self.endpoint, path), method=method, **kwargs)
        except TimeoutError:
            # Re-raise this directly so that it can be handled specially by
            # callers.
            raise
        except requests.RequestException:
            raise
        except Exception:
            _, val, tb = sys.exc_info()
            reraise(
                RequestExceptionWrapper, RequestExceptionWrapper(*val.args),
                tb)
        finally:
            action.finish()
        if as_json:
            if response.content:
                return response.json()
            else:
                return None
        else:
            return response.content

    def _get(self, branch_id, tail, **kwargs):
        return self._request("get", branch_id, tail, **kwargs)

    def _checkRevision(self, rev):
        """Check that a revision is well-formed.

        We don't have a lot of scope for validation here, since Bazaar
        allows revision IDs to be basically anything; but let's at least
        exclude / as an extra layer of defence against path traversal
        attacks.
        """
        if rev is not None and "/" in rev:
            raise ValueError("Revision ID '%s' is not well-formed." % rev)

    def getDiff(self, branch_id, new, old=None, context_lines=None,
                logger=None):
        """See `IBranchHostingClient`."""
        self._checkRevision(old)
        self._checkRevision(new)
        try:
            if logger is not None:
                if old is None:
                    logger.info(
                        "Requesting diff for %s from parent of %s to %s" %
                        (branch_id, new, new))
                else:
                    logger.info(
                        "Requesting diff for %s from %s to %s" %
                        (branch_id, old, new))
            quoted_tail = "diff/%s" % quote(new, safe="")
            if old is not None:
                quoted_tail += "/%s" % quote(old, safe="")
            return self._get(
                branch_id, quoted_tail, as_json=False,
                params={"context_lines": context_lines})
        except requests.RequestException as e:
            raise BranchHostingFault(
                "Failed to get diff from Bazaar branch: %s" % e)

    def getInventory(self, branch_id, dirname, rev=None, logger=None):
        """See `IBranchHostingClient`."""
        self._checkRevision(rev)
        try:
            if logger is not None:
                logger.info(
                    "Requesting inventory at %s from branch %s" %
                    (dirname, branch_id))
            quoted_tail = "files/%s/%s" % (
                quote(rev or "head:", safe=""), quote(dirname.lstrip("/")))
            return self._get(branch_id, quoted_tail, as_json=True)
        except requests.RequestException as e:
            if e.response.status_code == requests.codes.NOT_FOUND:
                raise BranchFileNotFound(branch_id, filename=dirname, rev=rev)
            else:
                raise BranchHostingFault(
                    "Failed to get inventory from Bazaar branch: %s" % e)

    def getBlob(self, branch_id, file_id, rev=None, logger=None):
        """See `IBranchHostingClient`."""
        self._checkRevision(rev)
        try:
            if logger is not None:
                logger.info(
                    "Fetching file ID %s from branch %s" %
                    (file_id, branch_id))
            return self._get(
                branch_id,
                "download/%s/%s" % (
                    quote(rev or "head:", safe=""), quote(file_id, safe="")),
                as_json=False)
        except requests.RequestException as e:
            if e.response.status_code == requests.codes.NOT_FOUND:
                raise BranchFileNotFound(branch_id, file_id=file_id, rev=rev)
            else:
                raise BranchHostingFault(
                    "Failed to get file from Bazaar branch: %s" % e)
