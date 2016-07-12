# Copyright 2011-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View tests for Product pages."""

__metaclass__ = type

import re
from urlparse import urlsplit

from testtools.matchers import Not
import soupmatchers
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.services.config import config
from lp.services.webapp import canonical_url
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class TestProductSetBranchView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_git_ssh_url(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            view = create_initialized_view(
                project, '+configure-code', principal=project.owner,
                method='GET')
            git_ssh_url = 'git+ssh://{username}@{host}/{project}'.format(
                username=project.owner.name,
                host=urlsplit(config.codehosting.git_ssh_root).netloc,
                project=project.name)
            self.assertEqual(git_ssh_url, view.git_ssh_url)


class TestBrowserProductSetBranchView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    editsshkeys_tag = soupmatchers.Tag(
        'edit SSH keys', 'a', text=re.compile('register an SSH key'),
        attrs={'href': re.compile(r'/\+editsshkeys$')})

    def getBrowser(self, project, view_name=None):
        project = removeSecurityProxy(project)
        url = canonical_url(project, view_name=view_name)
        return self.getUserBrowser(url, project.owner)

    def test_no_initial_git_repository(self):
        # If a project has no default Git repository, its "Git repository"
        # control defaults to empty.
        project = self.factory.makeProduct()
        browser = self.getBrowser(project, '+configure-code')
        self.assertEqual('', browser.getControl('Git repository').value)

    def test_initial_git_repository(self):
        # If a project has a default Git repository, its "Git repository"
        # control defaults to the unique name of that repository.
        project = self.factory.makeProduct()
        repo = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(project, repo)
        unique_name = repo.unique_name
        browser = self.getBrowser(project, '+configure-code')
        self.assertEqual(
            unique_name, browser.getControl('Git repository').value)

    def test_link_existing_git_repository(self):
        repo = removeSecurityProxy(self.factory.makeGitRepository(
            target=self.factory.makeProduct()))
        browser = self.getBrowser(repo.project, '+configure-code')
        browser.getControl('Git', index=0).click()
        browser.getControl('Git repository').value = repo.shortened_path
        browser.getControl('Update').click()

        tag = soupmatchers.Tag(
            'success-div', 'div', attrs={'class': 'informational message'},
             text='Project settings updated.')
        self.assertThat(browser.contents, soupmatchers.HTMLContains(tag))

    def test_editsshkeys_link_if_no_keys_registered(self):
        project = self.factory.makeProduct()
        browser = self.getBrowser(project, '+configure-code')
        self.assertThat(
            browser.contents, soupmatchers.HTMLContains(self.editsshkeys_tag))

    def test_no_editsshkeys_link_if_keys_registered(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            self.factory.makeSSHKey(person=project.owner)
        browser = self.getBrowser(project, '+configure-code')
        self.assertThat(
            browser.contents,
            Not(soupmatchers.HTMLContains(self.editsshkeys_tag)))
