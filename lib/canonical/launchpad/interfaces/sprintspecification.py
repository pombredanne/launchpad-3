# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for linking between Sprint and a Specification."""

__metaclass__ = type

__all__ = [
    'ISprintSpecification',
    ]

from zope.interface import Interface
from zope.schema import Bool, Choice, Int
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ISprintSpecification(Interface):
    """A link between a Sprint and a Specification."""

    sprint = Choice(title=_('Sprint'), required=True, readonly=True,
        description=_("Please select the sprint at which this spec will "
        "be discussed or implemented."), vocabulary='Sprint')
    specification = Int(title=_('Specification'), required=True,
        readonly=True)
    status = Choice(title=_('Agenda Status'), required=True,
        vocabulary='SprintSpecificationStatus')
    needs_discussion = Bool(title=_('Needs further discussion'),
        required=True, description=_("Check this to indicate that the "
        "specification needs further group discussion before drafting "
        "can continue."))

