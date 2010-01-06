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

    is_admin = None
    is_bazaar_expert = None
    is_bug_importer = None
    is_bug_watch_updater = None
    is_buildd_admin = None
    is_commercial_admin = None
    is_in_hwdb_team = None
    is_janitor = None
    is_katie = None
    is_lp_beta_tester = None
    is_lp_developer = None
    is_mailing_list_expert = None
    is_ppa_key_guard = None
    is_registry_expert = None
    is_rosetta_expert = None
    is_shipit_admin = None
    is_in_ubuntu_branches = None
    is_in_ubuntu_security = None
    is_in_ubuntu_techboard = None
    is_in_vcs_imports = None

    def inTeam(self, team):
        """See IPersonRoles."""

    def isOwner(self, obj):
        """See IPersonRoles."""

    def isDriver(self, obj):
        """See IPersonRoles."""

    def isOneOf(self, obj, attr):
        """See IPersonRoles."""

