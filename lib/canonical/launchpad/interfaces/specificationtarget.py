# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for things which have Specifications."""

__metaclass__ = type

__all__ = [
    'IHasSpecifications',
    'ISpecificationTarget',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IHasSpecifications(Interface):
    """An object that has specifications attached to it.
    
    For example, people, products and distributions have specificaitons
    associated with them, and you can use this interface to query those.
    """

    def specifications(quantity=None):
        """All the specifications for this target, sorted newest first.

        If there is a quantity, then limit it to that number.
        """


class ISpecificationTarget(IHasSpecifications):
    """An interface for the objects which actually have unique
    specifications directly attached to them.
    """

    def getSpecification(name):
        """Returns the specification with the given name, for this target,
        or None.
        """


