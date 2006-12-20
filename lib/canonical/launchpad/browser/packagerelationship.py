# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Package relationships."""

__metaclass__ = type
__all__ = [
    'PackageRelationship',
    'relationship_builder',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import IPackageRelationship
from canonical.launchpad.webapp import canonical_url


def relationship_builder(relationship_line, parser, getter):
    """Parse relationship_line into a list of IPackageRelationship.

    'relationship_line' is parsed via given 'parser' funcion
    It also lookup the corresponding URL via the given 'getter'.
    Return empty list if no line is given.
    """
    pkg_relationships = []

    if not relationship_line:
        return pkg_relationships

    parsed_relationships = [
        token[0] for token in parser(relationship_line)]

    for name, version, signal in parsed_relationships:
        target_object = getter(name)

        if target_object is not None:
            url = canonical_url(target_object)
        else:
            url = None

        pkg_relationships.append(
            PackageRelationship(name, signal, version, url))

    return pkg_relationships


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

