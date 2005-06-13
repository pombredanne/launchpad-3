"""General App Components for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""
__metaclass__ = type

from string import strip

from zope.interface import implements

from canonical.launchpad.interfaces import IbuilddepsSet


class builddepsSet:
    implements(IbuilddepsSet)

    def __init__(self, name, version, signal):
        self.name = name
        self.version = version
        if len(strip(signal)) == 0:
            signal = None
        self.signal = signal
