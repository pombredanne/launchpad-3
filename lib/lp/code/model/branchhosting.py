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
    urlencode,
    urljoin,
    )
from zope.interface import implementer

from lp.code.errors import (
    BranchFileNotFound,
    BranchHostingFault,
    )
from lp.code.interfaces.branchhosting import IBranchHostingClient
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

    def _request(self, method, unique_name, quoted_tail, as_json=False,
                 **kwargs):
        """Make a request to the Loggerhead API."""
        # Fetch the current timeout before starting the timeline action,
        # since making a database query inside this action will result in an
        # OverlappingActionError.
        get_default_timeout_function()()
        timeline = get_request_timeline(get_current_browser_request())
        if as_json:
            components = [unique_name, "+json", quoted_tail]
        else:
            components = [unique_name, quoted_tail]
        path = "/" + "/".join(components)
        action = timeline.start(
            "branch-hosting-%s" % method, "%s %s" % (path, json.dumps(kwargs)))
        try:
            response = urlfetch(
                urljoin(self.endpoint, path), trust_env=False, method=method,
                **kwargs)
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

    def _get(self, unique_name, tail, **kwargs):
        return self._request("get", unique_name, tail, **kwargs)

    def getDiff(self, unique_name, old, new, context_lines=None, logger=None):
        """See `IBranchHostingClient`."""
        try:
            if logger is not None:
                logger.info(
                    "Requesting diff for %s from %s to %s" %
                    (unique_name, old, new))
            quoted_tail = "diff/%s/%s" % (
                quote(new, safe=""), quote(old, safe=""))
            return self._get(
                unique_name, quoted_tail, as_json=False,
                params={"context_lines": context_lines})
        except requests.RequestException as e:
            raise BranchHostingFault(
                "Failed to get diff from Bazaar branch: %s" % e)

    def getInventory(self, unique_name, dirname, rev=None, logger=None):
        """See `IBranchHostingClient`."""
        try:
            if logger is not None:
                logger.info(
                    "Requesting inventory at %s from branch %s" %
                    (dirname, unique_name))
            quoted_tail = "files/%s/%s" % (
                quote(rev or "head:", safe=""), quote(dirname.lstrip("/")))
            return self._get(unique_name, quoted_tail, as_json=True)
        except requests.RequestException as e:
            if e.response.status_code == requests.codes.NOT_FOUND:
                raise BranchFileNotFound(
                    unique_name, filename=dirname, rev=rev)
            else:
                raise BranchHostingFault(
                    "Failed to get inventory from Bazaar branch: %s" % e)

    def getBlob(self, unique_name, file_id, rev=None, logger=None):
        """See `IBranchHostingClient`."""
        try:
            if logger is not None:
                logger.info(
                    "Fetching file ID %s from branch %s" %
                    (file_id, unique_name))
            return self._get(
                unique_name,
                "download/%s/%s" % (
                    quote(rev or "head:", safe=""), quote(file_id, safe="")),
                as_json=False)
        except requests.RequestException as e:
            if e.response.status_code == requests.codes.NOT_FOUND:
                raise BranchFileNotFound(
                    unique_name, file_id=file_id, rev=rev)
            else:
                raise BranchHostingFault(
                    "Failed to get file from Bazaar branch: %s" % e)
