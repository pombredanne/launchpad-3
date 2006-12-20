# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Package relationship interfaces."""

__metaclass__ = type
__all__ = [
    'IPackageRelationship',
    'IPackageRelationshipSet',
    ]

from zope.interface import Interface, Attribute

class IPackageRelationship(Interface):
    """The details of a relationship with a package.

    For example, if package foo depends on package bar version 0.6-1 or later,
    the relationship of bar to foo is represented as:

     name: 'bar'
     signal: '>='
     version: '0.6-1'

    The 'signal' and 'version' attributes may be None.
    """

    name = Attribute("The name of the related package")
    signal = Attribute("The operation for version comparisons, e.g '>='")
    version = Attribute("The version related to")
    url = Attribute("URL to where this token should link to. It can be None, "
                    "in this case no link should be rendered.")

class IPackageRelationshipSet(Interface):
    """IPackageRelationShip aggregator."""

    def addContent(name, signal, version, url):
        """Aggregates a new IPackageRelationship with given parameters."""

    def has_items():
        """whether of not this container has relationships to render."""
