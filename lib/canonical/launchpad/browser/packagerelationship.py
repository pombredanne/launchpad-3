# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Package relationships."""

__metaclass__ = type
__all__ = [
    'PackageRelationship'
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import IPackageRelationship


class PackageRelationship:
    """See IPackageRelationship."""

    implements(IPackageRelationship)

    def __init__(self, name, signal, version):
        self.name = name
        self.version = version

        if len(signal.strip()) == 0:
            self.signal = None
        else:
            self.signal = signal

