# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces for linking between Spec and Bug."""

__metaclass__ = type

__all__ = [
    'ISpecificationBug',
    ]

from zope.schema import Object

from canonical.launchpad import _
from lp.blueprints.interfaces.specification import ISpecification
from lp.bugs.interfaces.buglink import IBugLink


class ISpecificationBug(IBugLink):
    """A link between a Bug and a specification."""

    specification = Object(title=_('The specification linked to the bug.'),
        required=True, readonly=True, schema=ISpecification)


