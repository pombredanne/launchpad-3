# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.registry.browser.distroseriesdifferencecomment`."""

__metaclass__ = type

from lxml import html

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestDistroSeriesDifferenceCommentFragment(TestCaseWithFactory):
    """`IDistroSeriesDifferenceComment` +latest-comment-fragment view."""

    layer = LaunchpadFunctionalLayer

    def test_render(self):
        comment_text = "_123456789" * 10
        comment = self.factory.makeDistroSeriesDifferenceComment(
            comment=comment_text)
        view = create_initialized_view(comment, '+latest-comment-fragment')
        root = html.fromstring(view())
        self.assertEqual("span", root.tag)
        self.assertEqual("%s..." % comment_text[:47], root.text.strip())
        self.assertEqual(
            "/~%s" % comment.comment_author.name,
            root.find("span").find("a").get("href"))
