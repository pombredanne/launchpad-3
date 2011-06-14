# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.registry.browser.distroseriesdifferencecomment`."""

__metaclass__ = type

from lxml import html
from zope.component import getUtility

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
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

    def test_comment_is_rendered_with_view_css_class(self):
        comment = self.factory.makeDistroSeriesDifferenceComment()
        view = create_initialized_view(comment, '+latest-comment-fragment')
        view.css_class = self.factory.getUniqueString()
        root = html.fromstring(view())
        self.assertEqual(view.css_class, root.find("span").get("class"))

    def test_view_css_class_is_empty_by_default(self):
        comment = self.factory.makeDistroSeriesDifferenceComment(
            comment=self.factory.getUniqueString())
        view = create_initialized_view(comment, '+latest-comment-fragment')
        self.assertEqual("", view.css_class)

    def test_view_css_class_has_error_sprite_if_from_janitor(self):
        comment = self.factory.makeDistroSeriesDifferenceComment(
            owner=getUtility(ILaunchpadCelebrities).janitor)
        view = create_initialized_view(comment, '+latest-comment-fragment')
        self.assertEqual("sprite error-icon", view.css_class)
