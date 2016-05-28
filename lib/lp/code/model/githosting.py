# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Communication with the Git hosting service."""

__metaclass__ = type
__all__ = [
    'GitHostingClient',
    ]

import json
from urllib import quote
from urlparse import urljoin

from lazr.restful.utils import get_current_browser_request
import requests
from zope.interface import implementer

from lp.code.errors import (
    GitRepositoryCreationFault,
    GitRepositoryDeletionFault,
    GitRepositoryScanFault,
    )
from lp.code.interfaces.githosting import IGitHostingClient
from lp.services.config import config
from lp.services.timeline.requesttimeline import get_request_timeline
from lp.services.timeout import urlfetch


class HTTPResponseNotOK(Exception):
    pass


@implementer(IGitHostingClient)
class GitHostingClient:
    """A client for the internal API provided by the Git hosting system."""

    def __init__(self):
        self.endpoint = config.codehosting.internal_git_api_endpoint

    def _request(self, method, path, **kwargs):
        timeline = get_request_timeline(get_current_browser_request())
        action = timeline.start(
            "git-hosting-%s" % method, "%s %s" % (path, json.dumps(kwargs)))
        try:
            response = urlfetch(
                urljoin(self.endpoint, path), trust_env=False, method=method,
                **kwargs)
        except requests.HTTPError as e:
            raise HTTPResponseNotOK(e.response.content)
        finally:
            action.finish()
        if response.content:
            return response.json()
        else:
            return None

    def _get(self, path, **kwargs):
        return self._request("get", path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request("post", path, **kwargs)

    def _patch(self, path, **kwargs):
        return self._request("patch", path, **kwargs)

    def _delete(self, path, **kwargs):
        return self._request("delete", path, **kwargs)

    def create(self, path, clone_from=None):
        """See `IGitHostingClient`."""
        try:
            if clone_from:
                request = {"repo_path": path, "clone_from": clone_from}
            else:
                request = {"repo_path": path}
            self._post("/repo", json=request)
        except Exception as e:
            raise GitRepositoryCreationFault(
                "Failed to create Git repository: %s" % unicode(e))

    def getProperties(self, path):
        """See `IGitHostingClient`."""
        try:
            return self._get("/repo/%s" % path)
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to get properties of Git repository: %s" % unicode(e))

    def setProperties(self, path, **props):
        """See `IGitHostingClient`."""
        try:
            self._patch("/repo/%s" % path, json=props)
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to set properties of Git repository: %s" % unicode(e))

    def getRefs(self, path):
        """See `IGitHostingClient`."""
        try:
            return self._get("/repo/%s/refs" % path)
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to get refs from Git repository: %s" % unicode(e))

    def getCommits(self, path, commit_oids, logger=None):
        """See `IGitHostingClient`."""
        commit_oids = list(commit_oids)
        try:
            if logger is not None:
                logger.info("Requesting commit details for %s" % commit_oids)
            return self._post(
                "/repo/%s/commits" % path, json={"commits": commit_oids})
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to get commit details from Git repository: %s" %
                unicode(e))

    def getLog(self, path, start, limit=None, stop=None, logger=None):
        """See `IGitHostingClient`."""
        try:
            if logger is not None:
                logger.info(
                    "Requesting commit log for %s: "
                    "start %s, limit %s, stop %s" %
                    (path, start, limit, stop))
            return self._get(
                "/repo/%s/log/%s" % (path, quote(start)),
                params={"limit": limit, "stop": stop})
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to get commit log from Git repository: %s" %
                unicode(e))

    def getDiff(self, path, old, new, common_ancestor=False,
                context_lines=None, logger=None):
        """See `IGitHostingClient`."""
        try:
            if logger is not None:
                logger.info(
                    "Requesting diff for %s from %s to %s" % (path, old, new))
            separator = "..." if common_ancestor else ".."
            url = "/repo/%s/compare/%s%s%s" % (
                path, quote(old), separator, quote(new))
            return self._get(url, params={"context_lines": context_lines})
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to get diff from Git repository: %s" % unicode(e))

    def getMergeDiff(self, path, base, head, prerequisite=None, logger=None):
        """See `IGitHostingClient`."""
        try:
            if logger is not None:
                logger.info(
                    "Requesting merge diff for %s from %s to %s" % (
                        path, base, head))
            url = "/repo/%s/compare-merge/%s:%s" % (
                path, quote(base), quote(head))
            return self._get(url, params={"sha1_prerequisite": prerequisite})
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to get merge diff from Git repository: %s" %
                unicode(e))

    def detectMerges(self, path, target, sources, logger=None):
        """See `IGitHostingClient`."""
        sources = list(sources)
        try:
            if logger is not None:
                logger.info(
                    "Detecting merges for %s from %s to %s" % (
                        path, sources, target))
            return self._post(
                "/repo/%s/detect-merges/%s" % (path, quote(target)),
                json={"sources": sources})
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to detect merges in Git repository: %s" % unicode(e))

    def delete(self, path, logger=None):
        """See `IGitHostingClient`."""
        try:
            if logger is not None:
                logger.info("Deleting repository %s" % path)
            self._delete("/repo/%s" % path)
        except Exception as e:
            raise GitRepositoryDeletionFault(
                "Failed to delete Git repository: %s" % unicode(e))

    def getBlob(self, path, filename, rev=None, logger=None):
        """See `IGitHostingClient`."""
        try:
            if logger is not None:
                logger.info(
                    "Fetching file %s from repository %s" % (filename, path))
            url = "/repo/%s/blob/%s" % (path, quote(filename))
            response = self._get(url, params={"rev": rev})
            blob = response["data"].decode("base64")
            if len(blob) != response["size"]:
                raise GitRepositoryScanFault(
                    "Unexpected size (%s vs %s)" % (
                        len(blob), response["size"]))
            return blob
        except Exception as e:
            raise GitRepositoryScanFault(
                "Failed to get file from Git repository: %s" % unicode(e))
