# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository views."""

__metaclass__ = type

__all__ = [
    'GitRepositoryBreadcrumb',
    'GitRepositoryContextMenu',
    'GitRepositoryURL',
    'GitRepositoryView',
    ]

from bzrlib import urlutils
from zope.interface import implements

from lp.app.browser.informationtype import InformationTypePortletMixin
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.config import config
from lp.services.webapp import (
    ContextMenu,
    LaunchpadView,
    Link,
    )
from lp.services.webapp.authorization import (
    check_permission,
    precache_permission_for_objects,
    )
from lp.services.webapp.breadcrumb import NameBreadcrumb
from lp.services.webapp.interfaces import ICanonicalUrlData


class GitRepositoryURL:
    """Git repository URL creation rules."""

    implements(ICanonicalUrlData)

    rootsite = "code"
    inside = None

    def __init__(self, repository):
        self.repository = repository

    @property
    def path(self):
        return self.repository.unique_name


class GitRepositoryBreadcrumb(NameBreadcrumb):

    @property
    def inside(self):
        return self.context.unique_name.split("/")[-1]


class GitRepositoryContextMenu(ContextMenu):
    """Context menu for `IGitRepository`."""

    usedfor = IGitRepository
    facet = "branches"
    links = ["source"]

    def source(self):
        """Return a link to the branch's browsing interface."""
        text = "Browse the code"
        url = self.context.getCodebrowseUrl()
        return Link(url, text, icon="info")


class GitRepositoryView(InformationTypePortletMixin, LaunchpadView):

    @property
    def page_title(self):
        return self.context.display_name

    label = page_title

    def initialize(self):
        super(GitRepositoryView, self).initialize()
        # Cache permission so that the private team owner can be rendered.  The
        # security adapter will do the job also but we don't want or need the
        # expense of running several complex SQL queries.
        authorised_people = [self.context.owner]
        if self.user is not None:
            precache_permission_for_objects(
                self.request, "launchpad.LimitedView", authorised_people)

    @property
    def anon_url(self):
        if self.context.visibleByUser(None):
            return urlutils.join(
                config.codehosting.git_anon_root, self.context.shortened_path)
        else:
            return None

    @property
    def ssh_url(self):
        if self.user is not None:
            return urlutils.join(
                config.codehosting.git_ssh_root, self.context.shortened_path)
        else:
            return None

    @property
    def user_can_push(self):
        """Whether the user can push to this branch."""
        return check_permission("launchpad.Edit", self.context)
