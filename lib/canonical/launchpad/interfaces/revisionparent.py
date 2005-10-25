# Copyright 2005 Canonical Ltd.  All rights reserved.

"""RevisionParent interfaces."""

__metaclass__ = type

__all__ = ['IRevisionParent']

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Int


_ = MessageIDFactory('launchpad')


class IRevisionParent(Interface):
    """The association between a revision and its parent revisions."""

    revision = Attribute("The descendant revision.")
    parent = Attribute("The parent revision.")

