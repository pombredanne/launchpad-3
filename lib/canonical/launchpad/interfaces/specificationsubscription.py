# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Specification subscription interfaces."""

__metaclass__ = type

__all__ = [
    'ISpecificationSubscription',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int
from canonical.launchpad import _

class ISpecificationSubscription(Interface):
    """A subscription for a person to a specification."""

    person = Choice(
            title=_('Subscriber'), required=True,
            vocabulary='ValidPersonOrTeam', readonly=True,
            description=_(
            'The person you would like to subscribe to this specification. '
            'They will be notified of the subscription by email, if they '
            'have an active launchpad account.')
            )
    specification = Int(title=_('Specification'), required=True,
        readonly=True)


