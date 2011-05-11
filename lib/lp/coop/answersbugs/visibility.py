# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugcomment module."""

__metaclass__ = type

__all__ = [
    'TestMessageVisibilityMixin',
    ]


class TestMessageVisibilityMixin:

    comment_text = "You can't see me."

    def makeHiddenMessage(self):
        pass

    def getView(self, context, user=None, no_login=False):
        pass

    def test_admin_can_see_comments(self):
        context = self.makeHiddenMessage()
        admin = self.factory.makeAdministrator()
        view = self.getView(context=context, user=admin)
        self.assertIn(self.comment_text, view.contents)

    def test_registry_can_see_comments(self):
        context = self.makeHiddenMessage()
        registry_expert = self.factory.makeRegistryExpert()
        view = self.getView(context=context, user=registry_expert)
        self.assertIn(self.comment_text, view.contents)

    def test_anon_cannot_see_comments(self):
        context = self.makeHiddenMessage()
        view = self.getView(context=context, no_login=True)
        self.assertNotIn(self.comment_text, view.contents)

    def test_random_cannot_see_comments(self):
        context = self.makeHiddenMessage()
        view = self.getView(context=context)
        self.assertNotIn(self.comment_text, view.contents)
