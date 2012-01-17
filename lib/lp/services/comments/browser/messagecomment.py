# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = ['MessageComment']


from lp.services.messages.interfaces.message import IMessage
from lp.services.propertycache import cachedproperty


class MessageComment:
    """Mixin to partially implement IComment in terms of IMessage."""

    extra_css_class = ''

    has_footer = False

    @property
    def display_attachments(self):
        return []

    @cachedproperty
    def comment_author(self):
        """The author of the comment."""
        return IMessage(self).owner

    @cachedproperty
    def has_body(self):
        """Is there body text?"""
        return bool(self.body_text)

    @cachedproperty
    def comment_date(self):
        """The date of the comment."""
        return IMessage(self).datecreated

    @property
    def body_text(self):
        return IMessage(self).text_contents
