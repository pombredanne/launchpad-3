"""Soyuz

(c) Canonical Software Ltd. 2004, all rights reserved.
"""
from zope.interface import implements
from canonical.launchpad.interfaces import ISoyuzApplication

__metaclass__ = type

class SoyuzApplication:
    """Something that URLs get attached to.  See configure.zcml."""
    implements(ISoyuzApplication)

# arch-tag: 095a4ca8-1a0f-4287-bb2d-fdd0d48b576b
