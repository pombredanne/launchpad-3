"""Soyuz

(c) Canonical Software Ltd. 2004, all rights reserved.
"""
from zope.interface import implements
from canonical.launchpad.interfaces import ISoyuzApplication
from canonical.launchpad.database import Distribution

__metaclass__ = type

class SoyuzApplication(object):
    """The core Soyuz application object. This is really just a placeholder
    for traversal purposes."""
    implements(ISoyuzApplication)

    def distributions(self):
        """See ISoyuzApplication."""
        dists = Distribution.select()
        distlist = []
        # only show distros that are actively managed through soyuz as
        # opposed to back-end monitored
        for dist in dists:
            if dist.name not in ['debian', 'redhat', 'fedora', 'gentoo']:
                distlist.append(dist)
        return distlist

