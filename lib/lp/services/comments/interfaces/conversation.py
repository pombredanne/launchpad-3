# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces to do with conversations on Launchpad entities."""

__metaclass__ = type
__all__ = [
    'IComment',
    'IConversation',
    ]


from zope.interface import Interface
from zope.schema import Bool

from canonical.launchpad import _
from lazr.restful.fields import CollectionField, Reference


class IComment(Interface):
    """A comment which may have a body or footer."""

    has_body = Bool(
        description=_("Does the comment have body text?"),
        readonly=True)

    has_footer = Bool(
        description=_("Does the comment have a footer?"),
        readonly=True)


class IConversation(Interface):
    """A conversation has a number of comments."""

    comments = CollectionField(
        value_type=Reference(schema=IComment),
        title=_('The comments in the conversation'))
