# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpful functions to enforce permissions."""

__metaclass__ = type

__all__ = [
    'is_admin',
    'is_admin_or_registry_expert',
    'is_admin_or_rosetta_expert',
    'is_registry_expert',
    'is_rosetta_expert',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities


def is_admin(user):
    """Check if the user is a Launchpad admin."""
    celebrities = getUtility(ILaunchpadCelebrities)
    return user.inTeam(celebrities.admin)


def is_rosetta_expert(user):
    """Check if the user is a Rosetta expert."""
    celebrities = getUtility(ILaunchpadCelebrities)
    return user.inTeam(celebrities.rosetta_experts)


def is_registry_expert(user):
    """Check if the user is a Registry expert."""
    celebrities = getUtility(ILaunchpadCelebrities)
    return user.inTeam(celebrities.registry_experts)


def is_admin_or_rosetta_expert(user):
    """Check if the user is a Launchpad admin or a Rosetta expert."""
    return is_admin(user) or is_rosetta_expert(user)


def is_admin_or_registry_expert(user):
    """Check if the user is a Launchpad admin or a registry expert."""
    return is_admin(user) or is_registry_expert(user)
