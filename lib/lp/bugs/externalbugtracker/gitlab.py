# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""GitLab ExternalBugTracker utility."""

__metaclass__ = type
__all__ = [
    'BadGitLabURL',
    'GitLab',
    ]

import httplib

import pytz
from six.moves.urllib.parse import (
    quote,
    quote_plus,
    urlunsplit,
    )

from lp.bugs.externalbugtracker import (
    BugTrackerConnectError,
    ExternalBugTracker,
    UnknownRemoteStatusError,
    UnparsableBugTrackerVersion,
    )
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.interfaces.externalbugtracker import UNKNOWN_REMOTE_IMPORTANCE
from lp.services.config import config
from lp.services.webapp.url import urlsplit


class BadGitLabURL(UnparsableBugTrackerVersion):
    """The GitLab Issues URL is malformed."""


class GitLab(ExternalBugTracker):
    """An `ExternalBugTracker` for dealing with GitLab issues."""

    batch_query_threshold = 0  # Always use the batch method.

    def __init__(self, baseurl):
        _, host, path, query, fragment = urlsplit(baseurl)
        path = path.strip("/")
        if not path.endswith("/issues"):
            raise BadGitLabURL(baseurl)
        path = "/api/v4/projects/%s" % quote(path[:-len("/issues")], safe="")
        baseurl = urlunsplit(("https", host, path, query, fragment))
        super(GitLab, self).__init__(baseurl)
        self.cached_bugs = {}

    @property
    def credentials(self):
        credentials_config = config["checkwatches.credentials"]
        # lazr.config.Section doesn't support get().
        try:
            token = credentials_config["%s.token" % self.basehost]
        except KeyError:
            token = None
        return {"token": token}

    def getModifiedRemoteBugs(self, bug_ids, last_accessed):
        """See `IExternalBugTracker`."""
        modified_bugs = self.getRemoteBugBatch(
            bug_ids, last_accessed=last_accessed)
        self.cached_bugs.update(modified_bugs)
        return list(modified_bugs)

    def getRemoteBug(self, bug_id):
        """See `ExternalBugTracker`."""
        bug_id = int(bug_id)
        if bug_id not in self.cached_bugs:
            self.cached_bugs[bug_id] = (
                self._getPage("issues/%s" % bug_id).json())
        return bug_id, self.cached_bugs[bug_id]

    def getRemoteBugBatch(self, bug_ids, last_accessed=None):
        """See `ExternalBugTracker`."""
        bug_ids = [int(bug_id) for bug_id in bug_ids]
        bugs = {
            bug_id: self.cached_bugs[bug_id]
            for bug_id in bug_ids if bug_id in self.cached_bugs}
        if set(bugs) == set(bug_ids):
            return bugs
        params = []
        if last_accessed is not None:
            since = last_accessed.astimezone(pytz.UTC).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
            params.append(("updated_after", since))
        params.extend(
            [("iids[]", str(bug_id))
             for bug_id in bug_ids if bug_id not in bugs])
        # Don't use urlencode, since we need to leave the key "iids[]"
        # unquoted, and we have no other keys that require quoting.
        qs = []
        for k, v in params:
            qs.append(k + "=" + quote_plus(v))
        page = "issues?%s" % "&".join(qs)
        for remote_bug in self._getCollection(page):
            # We're only interested in the bug if it's one of the ones in
            # bug_ids.
            if remote_bug["iid"] not in bug_ids:
                continue
            bugs[remote_bug["iid"]] = remote_bug
            self.cached_bugs[remote_bug["iid"]] = remote_bug
        return bugs

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`."""
        return UNKNOWN_REMOTE_IMPORTANCE

    def getRemoteStatus(self, bug_id):
        """See `ExternalBugTracker`."""
        remote_bug = self.bugs[int(bug_id)]
        return " ".join([remote_bug["state"]] + remote_bug["labels"])

    def convertRemoteImportance(self, remote_importance):
        """See `IExternalBugTracker`."""
        return BugTaskImportance.UNKNOWN

    def convertRemoteStatus(self, remote_status):
        """See `IExternalBugTracker`.

        A GitLab status consists of the state followed by optional labels.
        """
        state = remote_status.split(" ", 1)[0]
        if state == "opened":
            return BugTaskStatus.NEW
        elif state == "closed":
            return BugTaskStatus.FIXRELEASED
        else:
            raise UnknownRemoteStatusError(remote_status)

    def makeRequest(self, method, url, headers=None, last_accessed=None,
                    **kwargs):
        """See `ExternalBugTracker`."""
        if headers is None:
            headers = {}
        if last_accessed is not None:
            headers["If-Modified-Since"] = (
                last_accessed.astimezone(pytz.UTC).strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"))
        token = self.credentials["token"]
        if token is not None:
            headers["Private-Token"] = token
        return super(GitLab, self).makeRequest(method, url, headers=headers)

    def _getCollection(self, base_page, last_accessed=None):
        """Yield each item from a batched remote collection.

        If the collection has not been modified since `last_accessed`, yield
        no items.
        """
        page = base_page
        while page is not None:
            try:
                response = self._getPage(page, last_accessed=last_accessed)
            except BugTrackerConnectError as e:
                if (e.error.response is not None and
                        e.error.response.status_code == httplib.NOT_MODIFIED):
                    return
                else:
                    raise
            for item in response.json():
                yield item
            if "next" in response.links:
                page = response.links["next"]["url"]
            else:
                page = None
