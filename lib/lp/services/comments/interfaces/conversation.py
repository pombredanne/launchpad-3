# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Interfaces to do with conversations on Launchpad entities."""

__metaclass__ = type
__all__ = [
    'IComment',
    'IConversation',
    ]


from zope.interface import Attribute, Interface

from canonical.launchpad import _
from lazr.restful.fields import CollectionField, Reference


class IComment(Interface):
    """A comment which may have a body or activity."""

    header = Attribute('The comment header.')
    body = Attribute('The comment body.')
    activity = Attribute('The comment activity.')


class IConversation(Interface):
    """A conversation has a number of comments."""

    comments = CollectionField(
        value_type=Reference(schema=IComment),
        title=_('The comments in the conversation'))
