# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Launchpad Pillars share a namespace.

Pillars are currently Product, Project and Distribution.
"""

__metaclass__ = type

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import Int

from canonical.launchpad import _
from canonical.launchpad.fields import BlacklistableContentNameField
from canonical.launchpad.interfaces import NotFoundError


__all__ = ['IPillarName', 'IPillarNameSet', 'PillarNameField']


class IPillarName(Interface):
    id = Int(title=_('The PillarName ID'))
    name = Attribute('The name')
    product = Attribute('The project that has this name, or None')
    project = Attribute('The project that has this name, or None')
    distribution = Attribute('The distribution that has this name, or None')


class IPillarNameSet(Interface):
    def __contains__(name):
        """Return True if the given name is a Pillar."""

    def __getitem__(name):
        """Get a pillar by its name."""


class PillarNameField(BlacklistableContentNameField):

    errormessage = _(
            "%s is already in use by another product, project or distribution"
            )

    def _getByName(self, name):
        pillar_set = getUtility(IPillarNameSet)
        try:
            return pillar_set[name]
        except NotFoundError:
            return None

