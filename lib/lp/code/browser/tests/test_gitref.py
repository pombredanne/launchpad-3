# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for GitRefView."""

__metaclass__ = type

import re

import soupmatchers
from zope.component import getUtility

from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_view


class GitRefView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rendering(self):
        repository = self.factory.makeGitRepository(
            owner=self.factory.makePerson(name="person"),
            target=self.factory.makeProduct(name="target"),
            name=u"git")
        getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
            repository.owner, repository.target, repository, repository.owner)
        [ref] = self.factory.makeGitRefs(
            repository=repository, paths=[u"refs/heads/master"])
        view = create_view(ref, "+index")
        # To test the breadcrumbs we need a correct traversal stack.
        view.request.traversed_objects = [repository, ref, view]
        view.initialize()
        breadcrumbs_tag = soupmatchers.Tag(
            'breadcrumbs', 'ol', attrs={'class': 'breadcrumbs'})
        self.assertThat(
            view(),
            soupmatchers.HTMLContains(
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'git collection breadcrumb', 'a',
                        text='Git',
                        attrs={'href': re.compile(r'/\+git$')})),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'repository breadcrumb', 'a',
                        text='lp:~person/target',
                        attrs={'href': re.compile(
                            r'/~person/target/\+git/git')})),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'git ref breadcrumb', 'li',
                        text=re.compile(r'\smaster\s')))))
