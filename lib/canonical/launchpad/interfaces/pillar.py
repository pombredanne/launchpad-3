# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Launchpad Pillars share a namespace.

Pillars are currently Product, Project and Distribution.
"""

__metaclass__ = type

from zope.interface import Interface, Attribute
from zope.schema import Bool, Int, TextLine

from canonical.launchpad import _
from canonical.lazr.fields import CollectionField, Reference
from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, exported,
    operation_parameters, operation_returns_entry, export_read_operation)


__all__ = ['IPillar', 'IPillarName', 'IPillarNameSet']


class IPillar(Interface):
    active = exported(
        Bool(title=_('Active'),
             description=_("Whether or not this item is active.")))


class IPillarName(Interface):
    id = Int(title=_('The PillarName ID'))
    name = TextLine(title=u"The name.")
    product = Attribute('The project that has this name, or None')
    project = Attribute('The project that has this name, or None')
    distribution = Attribute('The distribution that has this name, or None')
    active = Attribute('The pillar is active')
    pillar = Attribute('The pillar object')


class IPillarNameSet(Interface):
    export_as_webservice_entry()

    def __contains__(name):
        """Return True if the given name is an active Pillar."""

    def __getitem__(name):
        """Get an active pillar by its name.

        If there's no pillar with the given name or there is one but it's
        inactive, raise NotFoundError.
        """

    @operation_parameters(name=TextLine(title=u"Pillar name"))
    @operation_returns_entry(IPillar)
    @export_read_operation()
    def getByName(name, ignore_inactive=False):
        """Return the pillar with the given name.

        If ignore_inactive is True, then only active pillars are considered.

        If no pillar is found, return None.
        """

    def count_search_matches(text):
        """Return the total number of Pillars matching :text:"""

    def search(text, limit):
        """Return at most limit Products/Projects/Distros matching :text:.

        The return value is a sequence of dicts, where each dict contain
        the name of the object it represents (one of 'product', 'project'
        or 'distribution'), that object's id, name, title, description and
        the rank of that object on this specific search.

        If limit is None, config.launchpad.default_batch_size will be used.

        The results are ordered descending by rank.
        """

    def add_featured_project(project):
        """Add a project to the featured project list."""

    def remove_featured_project(project):
        """Remove a project from the featured project list."""

    featured_projects = exported(
        CollectionField(
            title=_('Projects, project groups, and distributions that are '
                    'featured on the site.'),
            value_type=Reference(schema=IPillar))
        )

