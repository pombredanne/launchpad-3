# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Communication with the Git hosting service."""

__metaclass__ = type
__all__ = [
    'GitHostingClient',
    ]

from urlparse import urljoin

import requests

from lp.code.errors import GitRepositoryCreationFault
from lp.services.config import config


class GitHostingClient:
    """A client for the internal API provided by the Git hosting system."""

    @property
    def endpoint(self):
        return config.codehosting.internal_git_endpoint

    def _makeSession(self):
        session = requests.Session()
        session.trust_env = False
        return session

    def create(self, path):
        response = self._makeSession().post(
            urljoin(self.endpoint, "create"), data={"path": path})
        if response.status_code != 200:
            raise GitRepositoryCreationFault(
                "Failed to create Git repository: %s" % response.text)
