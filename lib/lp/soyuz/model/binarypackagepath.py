# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'BinaryPackagePath',
    ]

from storm.locals import (
    Int,
    Storm,
    Unicode,
    )
from zope.interface import implements

from canonical.launchpad.interfaces.lpstorm import IMasterStore
from lp.soyuz.interfaces.binarypackagepath import IBinaryPackagePath


class BinaryPackagePath(Storm):
    """See `IBinaryPackagePath`."""
    implements(IBinaryPackagePath)
    __storm_table__ = 'BinaryPackagePath'
    id = Int(primary=True)
    path = Unicode(name='path', allow_none=False)

    def getOrCreate(self, path):
        """See `IBinaryPackagePathSource`."""
        store = IMasterStore(BinaryPackagePath)
        bpp = store.find(BinaryPackagePath, BinaryPackagePath.path == path)
        if bpp.count():
            return bpp[0]
        else:
            bpp = BinaryPackagePath()
            bpp.path = path
            return store.add(bpp)
