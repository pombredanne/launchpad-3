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
        self.inTeam = self.person.inTeam

    @property
    def is_admin(self):
        return self.person.inTeam(self._celebrities.admin)

    @property
    def is_bazaar_expert(self):
        return self.person.inTeam(self._celebrities.bazaar_experts)

    @property
    def is_bug_importer(self):
        return self.person.inTeam(self._celebrities.bug_importer)

    @property
    def is_bug_watch_updater(self):
        return self.person.inTeam(self._celebrities.bug_watch_updater)

    @property
    def is_buildd_admin(self):
        return self.person.inTeam(self._celebrities.buildd_admin)

    @property
    def is_commercial_admin(self):
        return self.person.inTeam(self._celebrities.commercial_admin)

    @property
    def is_in_hwdb_team(self):
        return self.person.inTeam(self._celebrities.hwdb_team)

    @property
    def is_janitor(self):
        return self.person.inTeam(self._celebrities.janitor)

    @property
    def is_katie(self):
        return self.person.inTeam(self._celebrities.katie)

    @property
    def is_lp_beta_tester(self):
        return self.person.inTeam(self._celebrities.launchpad_beta_testers)

    @property
    def is_lp_developer(self):
        return self.person.inTeam(self._celebrities.launchpad_developers)

    @property
    def is_mailing_list_expert(self):
        return self.person.inTeam(self._celebrities.mailing_list_experts)

    @property
    def is_ppa_key_guard(self):
        return self.person.inTeam(self._celebrities.ppa_key_guard)

    @property
    def is_registry_expert(self):
        return self.person.inTeam(self._celebrities.registry_experts)

    @property
    def is_rosetta_expert(self):
        return self.person.inTeam(self._celebrities.rosetta_experts)

    @property
    def is_shipit_admin(self):
        return self.person.inTeam(self._celebrities.shipit_admin)

    @property
    def is_in_ubuntu_branches(self):
        return self.person.inTeam(self._celebrities.ubuntu_branches)

    @property
    def is_in_ubuntu_security(self):
        return self.person.inTeam(self._celebrities.ubuntu_security)

    @property
    def is_in_ubuntu_techboard(self):
        return self.person.inTeam(self._celebrities.ubuntu_techboard)

    @property
    def is_in_vcs_imports(self):
        return self.person.inTeam(self._celebrities.vcs_imports)

    def isOwner(self, obj):
        """See IPersonRoles."""
        return self.person.inTeam(obj.owner)

    def isDriver(self, obj):
        """See IPersonRoles."""
        drivers = getattr(obj, 'drivers', None)
        if drivers is None:
            return self.person.inTeam(obj.driver)
        for driver in drivers:
            if self.person.inTeam(driver):
                return True
        return False

    def isOneOf(self, obj, attributes):
        """See IPersonRoles."""
        for attr in attributes:
            role = getattr(obj, attr)
            if self.person.inTeam(role):
                return True
        return False

