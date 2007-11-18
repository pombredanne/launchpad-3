# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for linking between Spec and Bug."""

__metaclass__ = type

__all__ = [
    'ISpecificationBug',
    ]

from zope.schema import Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.buglink import IBugLink
from canonical.launchpad.interfaces.specification import ISpecification

class ISpecificationBug(IBugLink):
    """A link between a Bug and a specification."""

    specification = Object(title=_('The specification linked to the bug.'),
        required=True, readonly=True, schema=ISpecification)


