# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Package relationships."""

__metaclass__ = type
__all__ = [
    'relationship_builder',
    'PackageRelationship',
    'PackageRelationshipSet',
    ]

import operator as std_operator

from debian.deb822 import PkgRelation
from zope.interface import implementer

from lp.services.webapp import canonical_url
from lp.soyuz.interfaces.packagerelationship import (
    IPackageRelationship,
    IPackageRelationshipSet,
    )


def relationship_builder(relationship_line, getter):
    """Parse relationship_line into a IPackageRelationshipSet.

    'relationship_line' is parsed via PkgRelation.parse_relations.
    It also looks up the corresponding URL via the given 'getter'.
    Return empty list if no line is given.
    """
    relationship_set = PackageRelationshipSet()

    if not relationship_line:
        return relationship_set

    parsed_relationships = [
        token[0] for token in PkgRelation.parse_relations(relationship_line)]

    for rel in parsed_relationships:
        name = rel['name']
        target_object = getter(name)
        if target_object is not None:
            url = canonical_url(target_object)
        else:
            url = None
        if rel['version'] is None:
            operator = ''
            version = ''
        else:
            operator, version = rel['version']
        relationship_set.add(name, operator, version, url)

    return relationship_set


@implementer(IPackageRelationship)
class PackageRelationship:
    """See IPackageRelationship."""

    def __init__(self, name, operator, version, url=None):
        self.name = name
        self.version = version
        self.url = url

        if len(operator.strip()) == 0:
            self.operator = None
        else:
            self.operator = operator


@implementer(IPackageRelationshipSet)
class PackageRelationshipSet:
    """See IPackageRelationshipSet."""

    def __init__(self):
        self.contents = []

    def add(self, name, operator, version, url):
        """See IPackageRelationshipSet."""
        self.contents.append(
            PackageRelationship(name, operator, version, url))

    def has_items(self):
        """See IPackageRelationshipSet."""
        return len(self.contents) is not 0

    def __iter__(self):
        return iter(sorted(
            self.contents, key=std_operator.attrgetter('name')))
