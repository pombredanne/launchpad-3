# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Package relationships."""

__metaclass__ = type
__all__ = [
    'relationship_builder',
    'PackageRelationship',
    'PackageRelationshipSet',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import (
    IPackageRelationship, IPackageRelationshipSet)
from canonical.launchpad.webapp import canonical_url


def relationship_builder(relationship_line, parser, getter):
    """Parse relationship_line into a IPackageRelationshipSet.

    'relationship_line' is parsed via given 'parser' funcion
    It also lookup the corresponding URL via the given 'getter'.
    Return empty list if no line is given.
    """
    relationship_set = PackageRelationshipSet()

    if not relationship_line:
        return relationship_set

    parsed_relationships = [
        token[0] for token in parser(relationship_line)]

    for name, version, signal in parsed_relationships:
        target_object = getter(name)
        if target_object is not None:
            url = canonical_url(target_object)
        else:
            url = None
        relationship_set.addContent(name, signal, version, url)

    return relationship_set


class PackageRelationship:
    """See IPackageRelationship."""

    implements(IPackageRelationship)

    def __init__(self, name, signal, version, url=None):
        self.name = name
        self.version = version
        self.url = url

        if len(signal.strip()) == 0:
            self.signal = None
        else:
            self.signal = signal


class PackageRelationshipSet:
    """See IPackageRelationshipSet."""
    implements(IPackageRelationshipSet)

    def __init__(self):
        self.contents = []

    def addContent(self, name, signal, version, url):
        """See IPackageRelationshipSet."""
        self.contents.append(
            PackageRelationship(name, signal, version, url))

    def has_items(self):
        """See IPackageRelationshipSet."""
        return len(self.contents) is not 0

    def __iter__(self):
        return iter(self.contents)

