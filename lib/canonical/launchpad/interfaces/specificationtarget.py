# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for things which have Specifications."""

__metaclass__ = type

__all__ = [
    'IHasSpecifications',
    'ISpecificationTarget',
    'ISpecificationGoal',
    ]

from zope.interface import Interface, Attribute

from canonical.launchpad import _

class IHasSpecifications(Interface):
    """An object that has specifications attached to it.

    For example, people, products and distributions have specifications
    associated with them, and you can use this interface to query those.
    """

    all_specifications = Attribute(
        'A list of all specifications, regardless of status or approval '
        'or completion, for this object.')

    has_any_specifications = Attribute(
        'A true or false indicator of whether or not this object has any '
        'specifications associated with it, regardless of their status.')

    valid_specifications = Attribute(
        'A list of all specifications that are not obsolete.')

    latest_specifications = Attribute(
        "The latest 5 specifications registered for this context.")

    latest_completed_specifications = Attribute(
        "The 5 specifications most recently completed for this context.")

    def specifications(quantity=None, sort=None, filter=None):
        """Specifications for this target.

        The sort is a dbschema which indicates the preferred sort order. The
        filter is an indicator of the kinds of specs to be returned, and
        appropriate filters depend on the kind of object this method is on.
        If there is a quantity, then limit the result to that number.

        In the case where the filter is [] or None, the content class will
        decide what its own appropriate "default" filter is. In some cases,
        it will show all specs, in others, all approved specs, and in
        others, all incomplete specs.
        """



class ISpecificationTarget(IHasSpecifications):
    """An interface for the objects which actually have unique
    specifications directly attached to them.
    """

    def getSpecification(name):
        """Returns the specification with the given name, for this target,
        or None.
        """


class ISpecificationGoal(ISpecificationTarget):
    """An interface for those things which can have specifications proposed
    as goals for them.
    """


