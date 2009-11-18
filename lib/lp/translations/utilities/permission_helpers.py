# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpful functions to enforce permissions."""

__metaclass__ = type

__all__ = [
    'is_admin_or_rosetta_expert',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities


def is_admin_or_rosetta_expert(user):
    """Check if the user is a Launchpad admin or a Rosettta expert."""
    celebrities = getUtility(ILaunchpadCelebrities)
    return (user.inTeam(celebrities.admin) or
            user.inTeam(celebrities.rosetta_experts))
