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


class PersonRoles(object):
    implements(IPersonRoles)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person
