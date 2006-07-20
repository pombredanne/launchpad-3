# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Launchpad Pillars share a namespace.

Pillars are currently Product, Project and Distribution.
"""

__metaclass__ = type

from zope.interface import Interface

__all__ = ['IPillarSet']

class IPillarSet(Interface):
    def __contains__(name):
        """Return True if the given name is a Pillar."""

    def __getitem__(name):
        """Get a pillar by its name."""

