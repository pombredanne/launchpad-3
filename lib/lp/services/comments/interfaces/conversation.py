# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Interfaces to do with conversations on Launchpad entities."""

__metaclass__ = type
__all__ = [
    'IComment',
    'ICommentActivity',
    'ICommentBody',
    'IConversation',
    ]


from zope.interface import Interface

from canonical.launchpad import _
from lazr.restful.fields import CollectionField, Reference


class ICommentBody(Interface):
    """A marker interface to indicate a ..."""


class ICommentActivity(Interface):
    """A ..."""


class IComment(Interface):
    """A comment which may have a body or activity."""

    body = Reference(schema=ICommentBody, title=_('The comment body.'))
    activity = Reference(schema=ICommentActivity, title=_('The activity.'))


class IConversation(Interface):
    """A conversation has a number of comments."""

    comments = CollectionField(
        value_type=Reference(schema=IComment),
        title=_('The comments in the conversation'))
