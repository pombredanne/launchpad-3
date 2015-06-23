# Copyright 2011-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View tests for Product pages."""

__metaclass__ = type

import soupmatchers
from zope.security.proxy import removeSecurityProxy

from lp.services.webapp import canonical_url
from lp.testing import BrowserTestCase
from lp.testing.layers import DatabaseFunctionalLayer


class TestProductSetBranchView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def getBrowser(self, project, view_name=None):
        project = removeSecurityProxy(project)
        url = canonical_url(project, view_name=view_name)
        return self.getUserBrowser(url, project.owner)

    def test_link_existing_git_repository(self):
        repo = removeSecurityProxy(self.factory.makeProductGitRepository())
        browser = self.getBrowser(repo.project, '+configure-code')
        browser.getControl('Git', index=0).click()
        browser.getControl('Git Repository').value = repo.shortened_path
        browser.getControl('Update').click()

        tag = soupmatchers.Tag(
            'success-div', 'div', attrs={'class': 'informational message'},
             text='Project code updated.')
        self.assertThat(browser.contents, soupmatchers.HTMLContains(tag))
