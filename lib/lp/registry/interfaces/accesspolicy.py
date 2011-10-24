# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for pillar and artifact access policies."""

__metaclass__ = type

__all__ = [
    'IAccessPolicy',
    'IAccessPolicyArtifact',
    'IAccessPolicyArtifactSource',
    'IAccessPolicyPermission',
    'IAccessPolicySource',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )


class IAccessPolicy(Interface):
    id = Attribute("ID")
    pillar = Attribute("Pillar")
    display_name = Attribute("Display name")
    permissions = Attribute("Permissions")


class IAccessPolicyArtifact(Interface):
    id = Attribute("ID")
    concrete_artifact = Attribute("Concrete artifact")


class IAccessPolicyPermission(Interface):
    id = Attribute("ID")
    policy = Attribute("Access policy")
    person = Attribute("Person")
    abstract_artifact = Attribute("Abstract artifact")
    concrete_artifact = Attribute("Concrete artifact")


class IAccessPolicySource(Interface):

    def create(pillar, display_name):
        """Create an `IAccessPolicy` for the pillar with the given name."""

    def getByID(id):
        """Return the `IAccessPolicy` with the given ID."""

    def getByPillarAndName(pillar, display_name):
        """Return the pillar's `IAccessPolicy` with the given name."""

    def findByPillar(pillar):
        """Return a ResultSet of all `IAccessPolicy`s for the pillar."""


class IAccessPolicyArtifactSource(Interface):

    def ensure(concrete_artifact):
        """Return the `IAccessPolicyArtifact` for a concrete artifact.

        Creates the abstract artifact if it doesn't already exist.
        """
