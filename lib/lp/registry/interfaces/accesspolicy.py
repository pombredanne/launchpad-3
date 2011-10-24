# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for pillar and artifact access policies."""

__metaclass__ = type

__all__ = [
    'IAccessPolicy',
    'IAccessPolicyArtifact',
    'IAccessPolicyPermission',
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
