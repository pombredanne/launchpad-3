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
        return Distribution.select()

