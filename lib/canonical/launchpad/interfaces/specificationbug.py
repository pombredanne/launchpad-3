# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for linking between Spec and Bug."""

__metaclass__ = type

__all__ = [
    'ISpecificationBug',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int

from canonical.launchpad import _

class ISpecificationBug(Interface):
    """A link between a Bug and a specification."""

    specification = Int(title=_('Specification ID'), required=True,
        readonly=True)
    bug = Int(title=_('Bug Number'), required=True, readonly=True,
        description=_("The number of the Malone bug report. This will "
        "record a relationship between the specification and the bug "
        "report, and make it easy to jump from the one page to the other "
        "in Launchpad."))


