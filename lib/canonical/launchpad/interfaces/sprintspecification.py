# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for linking between Sprint and a Specification."""

__metaclass__ = type

__all__ = [
    'ISprintSpecification',
    ]

from zope.interface import Interface
from zope.schema import Bool, Choice, Int, Text
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ISprintSpecification(Interface):
    """A link between a Sprint and a Specification."""

    sprint = Choice(title=_('Sprint'), required=True, readonly=True,
        description=_("The meeting or sprint at which this specification will "
        "be discussed or implemented."), vocabulary='Sprint')
    specification = Int(title=_('Specification'), required=True,
        readonly=True)
    status = Choice(title=_('Agenda Status'), required=True,
        vocabulary='SprintSpecificationStatus')
    whiteboard = Text(title=_('Whiteboard'), required=False,
        description=_(
            "Any reasoning or rationale for the status you set here."
            "Your changes will override the current text. Note that "
            "this is purely related to this spec at this meeting, not "
            "the specification in general."))

