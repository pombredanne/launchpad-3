# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugcomment module."""

__metaclass__ = type

__all__ = [
    'TestMessageVisibilityMixin',
    'TestHideMessageControlMixin',
    ]


from canonical.launchpad.testing.pages import find_tag_by_id


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


class TestHideMessageControlMixin:

    def getContext(self):
        pass

    def getView(self, context, user=None, no_login=False):
        pass

    def test_admin_sees_hide_control(self):
        context = self.getContext()
        administrator = self.factory.makeAdministrator()
        view = self.getView(context=context, user=administrator)
        hide_link = find_tag_by_id(view.contents, 'mark-spam-1')
        self.assertIsNot(None, hide_link)

    def test_registry_sees_hide_control(self):
        context = self.getContext()
        registry_expert = self.factory.makeRegistryExpert()
        view = self.getView(context=context, user=registry_expert)
        contents = view.contents
        hide_link = find_tag_by_id(view.contents, 'mark-spam-1')
        self.assertIsNot(None, hide_link)

    def test_anon_doesnt_see_hide_control(self):
        context = self.getContext()
        view = self.getView(context=context, no_login=True)
        hide_link = find_tag_by_id(view.contents, 'mark-spam-1')
        self.assertIs(None, hide_link)

    def test_random_doesnt_see_hide_control(self):
        context = self.getContext()
        view = self.getView(context=context)
        hide_link = find_tag_by_id(view.contents, 'mark-spam-1')
        self.assertIs(None, hide_link)
