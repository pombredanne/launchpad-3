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
    'UnsuitableAccessPolicyError',
    ]

import httplib

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from lazr.restful.declarations import error_status
from zope.interface import (
    Attribute,
    Interface,
    )


@error_status(httplib.BAD_REQUEST)
class UnsuitableAccessPolicyError(Exception):
    pass


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

    def ensure(concrete_artifact):
        """Return the `IAccessArtifact` for a concrete artifact.

        Creates the abstract artifact if it doesn't already exist.
        """

    def get(concrete_artifact):
        """Return the `IAccessArtifact` for an artifact, if it exists.

        Use ensure() if you want to create one if it doesn't yet exist.
        """

    def delete(concrete_artifact):
        """Delete the `IAccessArtifact` for a concrete artifact.

        Also removes any AccessArtifactGrants for the artifact.
        """


class IAccessArtifactGrantSource(Interface):

    def grant(artifact, grantee, grantor):
        """Create an `IAccessArtifactGrant`.

        :param artifact: the `IAccessArtifact` to grant access to.
        :param grantee: the `IPerson` to hold the access.
        :param grantor: the `IPerson` that grants the access.
        """

    def get(artifact, grantee):
        """Return the specified `IAccessArtifactGrant` or None.

        :param artifact: the `IAccessArtifact` that access is granted to.
        :param grantee: the `IPerson` who holds the access.
        """

    def findByArtifact(artifact):
        """Return all `IAccessArtifactGrant` objects for the artifact."""


class IAccessPolicySource(Interface):

    def create(policies):
        """Create an `IAccessPolicy` for the given pillars and types.

        :param policies: a collection of
            (`IProduct` or `IDistribution`, `IAccessPolicyType`) pairs to
            create `IAccessPolicy` objects for.
        :return: a collection of the created `IAccessPolicy` objects.
        """

    def getByID(id):
        """Return the `IAccessPolicy` with the given ID."""

    def getByPillarAndType(pillar, type):
        """Return the pillar's `IAccessPolicy` with the given type."""

    def findByPillar(pillar):
        """Return a ResultSet of all `IAccessPolicy`s for the pillar."""


class IAccessPolicyGrantSource(Interface):

    def grant(policy, grantee, grantor):
        """Create an `IAccessPolicyGrant`.

        :param policy: the `IAccessPolicy` to grant access to.
        :param grantee: the `IPerson` to hold the access.
        :param grantor: the `IPerson` that grants the access.
        """

    def get(policy, grantee):
        """Return the specified `IAccessPolicyGrant` or None.

        :param policy: the `IAccessPolicy` that access is granted to.
        :param grantee: the `IPerson` who holds the access.
        """

    def findByPolicy(policy):
        """Return all `IAccessPolicyGrant` objects for the policy."""
