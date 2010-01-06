# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Class that implements the IPersonRoles interface."""

__metaclass__ = type
__all__ = ['PersonRoles']

from zope.interface import implements
from zope.component import adapts, getUtility
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IPersonRoles)

from lp.registry.interfaces.person import IPerson


class PersonRoles:
    implements(IPersonRoles)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person
        self._celebrities = getUtility(ILaunchpadCelebrities)

    @property
    def is_admin(self):
        return self.person.inTeam(self._celebrities.admin)

    is_bazaar_expert = False
    is_bug_importer = False
    is_bug_watch_updater = False
    is_buildd_admin = False
    is_commercial_admin = False
    is_in_hwdb_team = False
    is_janitor = False
    is_katie = False
    is_lp_beta_tester = False
    is_lp_developer = False
    is_mailing_list_expert = False
    is_ppa_key_guard = False
    is_registry_expert = False
    is_rosetta_expert = False
    is_shipit_admin = False
    is_in_ubuntu_branches = False
    is_in_ubuntu_security = False
    is_in_ubuntu_techboard = False
    is_in_vcs_imports = False

    def inTeam(self, team):
        """See IPersonRoles."""

    def isOwner(self, obj):
        """See IPersonRoles."""

    def isDriver(self, obj):
        """See IPersonRoles."""

    def isOneOf(self, obj, attr):
        """See IPersonRoles."""

