# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for pillar and artifact access policies."""

__metaclass__ = type

__all__ = [
    'IAccessArtifact',
    'IAccessArtifactGrant',
    'IAccessArtifactGrantSource',
    'IAccessArtifactSource',
    'IAccessPolicy',
    'IAccessPolicyArtifact',
    'IAccessPolicyArtifactSource',
    'IAccessPolicyGrant',
    'IAccessPolicyGrantFlatSource',
    'IAccessPolicyGrantSource',
    'IAccessPolicySource',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )


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


class IAccessPolicyArtifact(Interface):
    abstract_artifact = Attribute("Abstract artifact")
    policy = Attribute("Access policy")


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


class IAccessPolicyArtifactSource(Interface):

    def create(links):
        """Create `IAccessPolicyArtifacts`s.

        :param links: a collection of (`IAccessArtifact`, `IAccessPolicy`)
            pairs to link.
        """

    def find(links):
        """Return the specified `IAccessPolicyArtifacts`s if they exist.

        :param links: a collection of (`IAccessArtifact`, `IAccessPolicy`)
            pairs.
        """

    def findByArtifact(artifacts):
        """Return all `IAccessPolicyArtifact` objects for the artifacts."""

    def findByPolicy(policies):
        """Return all `IAccessPolicyArtifact` objects for the policies."""


class IAccessPolicySource(Interface):

    def create(pillars_and_types):
        """Create an `IAccessPolicy` for the given pillars and types.

        :param pillars_and_types: a collection of
            (`IProduct` or `IDistribution`, `IAccessPolicyType`) pairs to
            create `IAccessPolicy` objects for.
        :return: a collection of the created `IAccessPolicy` objects.
        """

    def find(pillars_and_types):
        """Return the `IAccessPolicy`s for the given pillars and types.

        :param pillars_and_types: a collection of
            (`IProduct` or `IDistribution`, `IAccessPolicyType`) pairs to
            find.
        """

    def findByID(ids):
        """Return the `IAccessPolicy`s with the given IDs."""

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
        """Return all `IAccessPolicyGrant` objects for the policies."""


class IAccessPolicyGrantFlatSource(Interface):

    def findGranteesByPolicy(policies):
        """Find the `IPerson`s with access grants for the policies.

        This includes grants for artifacts in the policies.

        :param policies: a collection of `IAccesPolicy`s.
        """
