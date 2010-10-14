# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces to do with conversations on Launchpad entities."""

__metaclass__ = type
__all__ = [
    'IComment',
    'IConversation',
    ]


from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import Interface
from zope.schema import (
    Bool,
    Datetime,
    Text,
    TextLine,
    )

from canonical.launchpad import _


class IComment(Interface):
    """A comment which may have a body or footer."""

    extra_css_class = TextLine(
        description=_("A css class to apply to the comment's outer div."))

    has_body = Bool(
        description=_("Does the comment have body text?"),
        readonly=True)

    has_footer = Bool(
        description=_("Does the comment have a footer?"),
        readonly=True)

    body_text = Text(
        description=_("The body text of the comment."),
        readonly=True)

    comment_author = Reference(
        # Really IPerson.
        Interface, title=_("The author of the comment."),
        readonly=True)

    comment_date = Datetime(
        title=_('Comment date.'), readonly=True)

    display_attachments = Bool(
        description=_("Should attachments be displayed for this comment."),
        readonly=True)


class IConversation(Interface):
    """A conversation has a number of comments."""

    comments = CollectionField(
        value_type=Reference(schema=IComment),
        title=_('The comments in the conversation'))
