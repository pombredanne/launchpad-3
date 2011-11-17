# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for pillar and artifact access policies."""

__metaclass__ = type

__all__ = [
    'AccessPolicyType',
    'IAccessPolicy',
    'IAccessPolicyArtifact',
    'IAccessPolicyArtifactSource',
    'IAccessPolicyGrant',
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


class IAccessPolicy(Interface):
    id = Attribute("ID")
    pillar = Attribute("Pillar")
    type = Attribute("Type")


class IAccessPolicyArtifact(Interface):
    id = Attribute("ID")
    concrete_artifact = Attribute("Concrete artifact")
    policy = Attribute("Access policy")


class IAccessPolicyGrant(Interface):
    id = Attribute("ID")
    grantee = Attribute("Grantee")
    grantor = Attribute("Grantor")
    date_created = Attribute("Date created")
    policy = Attribute("Access policy")
    abstract_artifact = Attribute("Abstract artifact")

    concrete_artifact = Attribute("Concrete artifact")


class IAccessPolicySource(Interface):

    def create(pillar, display_name):
        """Create an `IAccessPolicy` for the pillar with the given name."""

    def getByID(id):
        """Return the `IAccessPolicy` with the given ID."""

    def getByPillarAndType(pillar, type):
        """Return the pillar's `IAccessPolicy` with the given type."""

    def findByPillar(pillar):
        """Return a ResultSet of all `IAccessPolicy`s for the pillar."""


class IAccessPolicyArtifactSource(Interface):

    def ensure(concrete_artifact):
        """Return the `IAccessPolicyArtifact` for a concrete artifact.

        Creates the abstract artifact if it doesn't already exist.
        """


class IAccessPolicyGrantSource(Interface):

    def grant(grantee, grantor, object):
        """Create an `IAccessPolicyGrant`.

        :param grantee: the `IPerson` to hold the access.
        :param grantor: the `IPerson` that grants the access.
        :param object: the `IAccessPolicy` or `IAccessPolicyArtifact` to
            grant access to.
        """

    def getByID(id):
        """Return the `IAccessPolicyGrant` with the given ID."""

    def findByPolicy(policy):
        """Return all `IAccessPolicyGrant` objects for the policy."""
