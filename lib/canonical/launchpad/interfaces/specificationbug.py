# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for linking between Spec and Bug."""

__metaclass__ = type

__all__ = [
    'ISpecificationBug',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ISpecificationBug(Interface):
    """A link between a Bug and a specification."""

    specification = Int(title=_('Specification ID'), required=True,
        readonly=True)
    bug = Int(title=_('Bug Number'), required=True, readonly=True,
        description=_("The number of the Malone bug report."))


