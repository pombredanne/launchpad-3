# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for things which have Specifications."""

__metaclass__ = type

__all__ = [
    'ISpecificationTarget',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ISpecificationTarget(Interface):
    """An object that has specifications attached to it.
    
    Initially, only Products and Distributions can have specifications.
    """

    specifications = Attribute("All the specifications for this "
        "target, sorted newest first.")

    def getSpecification(name):
        """Returns the specification with the given name, for this target,
        or None.
        """


