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
    active = Attribute('The pillar is active')


class IPillarNameSet(Interface):
    def __contains__(name):
        """Return True if the given name is a Pillar."""

    def __getitem__(name):
        """Get a pillar by its name."""

    def search(text, limit):
        """Return at most limit Products/Projects/Distros matching :text:.

        The return value is a sequence of dicts, where each dict contain
        the name of the object it represents (one of 'product', 'project'
        or 'distribution'), that object's id, name, title, description and
        the rank of that object on this specific search.

        If limit is None, config.launchpad.default_batch_size will be used.

        The results are ordered descending by rank.
        """


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

