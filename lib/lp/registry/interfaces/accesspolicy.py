# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for pillar and artifact access policies."""

__metaclass__ = type

__all__ = [
    'AccessPolicyType',
    'IAccessArtifact',
    'IAccessArtifactGrant',
    'IAccessArtifactGrantSource',
    'IAccessArtifactSource',
    'IAccessPolicy',
    'IAccessPolicyGrant',
    'IAccessPolicyGrantSource',
    'IAccessPolicySource',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from zope.interface import (
    Attribute,
    Interface,
    )


class AccessPolicyType(DBEnumeratedType):
    """Access policy type."""

    PRIVATE = DBItem(1, """
        Private

        This policy covers general private information.
        """)

    SECURITY = DBItem(2, """
        Security

        This policy covers information relating to confidential security
        vulnerabilities.
        """)


class IAccessArtifact(Interface):
    id = Attribute("ID")
    concrete_artifact = Attribute("Concrete artifact")


class IAccessArtifactGrant(Interface):
    grantee = Attribute("Grantee")
    grantor = Attribute("Grantor")
    date_created = Attribute("Date created")
    abstract_artifact = Attribute("Abstract artifact")

    concrete_artifact = Attribute("Concrete artifact")


class IAccessPolicy(Interface):
    id = Attribute("ID")
    pillar = Attribute("Pillar")
    type = Attribute("Type")


class IAccessPolicyGrant(Interface):
    grantee = Attribute("Grantee")
    grantor = Attribute("Grantor")
    date_created = Attribute("Date created")
    policy = Attribute("Access policy")


class IAccessArtifactSource(Interface):

    def ensure(concrete_artifacts):
        """Return `IAccessArtifact`s for the concrete artifacts.

        Creates abstract artifacts if they don't already exist.
        """

    def find(concrete_artifacts):
        """Return the `IAccessArtifact`s for the artifacts, if they exist.

        Use ensure() if you want to create them if they don't yet exist.
        """

    def delete(concrete_artifacts):
        """Delete the `IAccessArtifact`s for the concrete artifact.

        Also revokes any `IAccessArtifactGrant`s for the artifacts.
        """


class IAccessArtifactGrantSource(Interface):

    def grant(grants):
        """Create `IAccessArtifactGrant`s.

        :param grants: a collection of
            (`IAccessArtifact`, grantee `IPerson`, grantor `IPerson`) triples
            to grant.
        """

    def find(grants):
        """Return the specified `IAccessArtifactGrant`s if they exist.

        :param grants: a collection of (`IAccessArtifact`, grantee `IPerson`)
            pairs.
        """

    def findByArtifact(artifacts):
        """Return all `IAccessArtifactGrant` objects for the artifacts."""

    def revokeByArtifact(artifacts):
        """Delete all `IAccessArtifactGrant` objects for the artifacts."""


class IAccessPolicySource(Interface):

    def create(policies):
        """Create an `IAccessPolicy` for the given pillars and types.

        :param policies: a collection of
            (`IProduct` or `IDistribution`, `IAccessPolicyType`) pairs to
            create `IAccessPolicy` objects for.
        :return: a collection of the created `IAccessPolicy` objects.
        """

    def findByID(ids):
        """Return the `IAccessPolicy`s with the given IDs."""

    def findByPillarAndType(pillars_and_types):
        """Return the `IAccessPolicy`s for the given pillars and types."""

    def findByPillar(pillars):
        """Return a `ResultSet` of all `IAccessPolicy`s for the pillars."""


class IAccessPolicyGrantSource(Interface):

    def grant(grants):
        """Create `IAccessPolicyGrant`s.

        :param grants: a collection of
            (`IAccessPolicy`, grantee `IPerson`, grantor `IPerson`) triples
            to grant.
        """

    def find(grants):
        """Return the specified `IAccessPolicyGrant`s if they exist.

        :param grants: a collection of (`IAccessPolicy`, grantee `IPerson`)
            pairs.
        """

    def findByPolicy(policies):
        """Return all `IAccessPolicyGrant` objects for the artifacts."""
