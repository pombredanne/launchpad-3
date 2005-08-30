# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Specification subscription interfaces."""

__metaclass__ = type

__all__ = [
    'ISpecificationSubscription',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ISpecificationSubscription(Interface):
    """A subscription for a person to a specification."""

    person = Choice(
            title=_('Person ID'), required=True, vocabulary='ValidPersonOrTeam',
            readonly=True,
            )
    specification = Int(title=_('Specification ID'), required=True,
        readonly=True)


