# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git references."""

__metaclass__ = type

from lp.code.interfaces.gitrepository import GIT_FEATURE_FLAG
from lp.services.features.testing import FeatureFixture
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitRef(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_display_name(self):
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))
        [master, personal] = self.factory.makeGitRefs(
            paths=[u"refs/heads/master", u"refs/heads/people/foo/bar"])
        self.assertEqual(
            ["master", "people/foo/bar"],
            [ref.display_name for ref in (master, personal)])
