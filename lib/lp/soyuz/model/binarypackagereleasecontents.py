# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'BinaryPackageReleaseContents',
    ]

from fixtures import TempDir
import os
import subprocess

from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.librarian.utils import copy_and_close
from lp.soyuz.interfaces.binarypackagepath import IBinaryPackagePathSource
from lp.soyuz.interfaces.binarypackagereleasecontents import (
    IBinaryPackageReleaseContents,
    )


class BinaryPackageReleaseContents(Storm):
    """See `IBinaryPackageReleaseContents`."""
    implements(IBinaryPackageReleaseContents)
    __storm_table__ = 'BinaryPackageReleaseContents'
    __storm_primary__ = ("binarypackagerelease_id", "binaypackagepath_id")

    binarypackagerelease_id = Int(
        name='binarypackagerelease', allow_none=False)
    binarypackagerelease = Reference(
        binarypackagerelease_id, 'BinaryPackageRelease.id')

    binaypackagepath_id = Int(name='binarypackagepath', allow_none=False)
    binarypackagepath = Reference(
        binaypackagepath_id, 'BinaryPackagePath.id')

    def add(self, bpr):
        """See `IBinaryPackageReleaseContents`."""
        if not bpr.files:
            return None
        store = IMasterStore(BinaryPackageReleaseContents)
        with TempDir() as tmp_dir:
            dest = os.path.join(
                tmp_dir.path, bpr.files[0].libraryfile.filename)
            dest_file = open(dest, 'w')
            bpr.files[0].libraryfile.open()
            copy_and_close(bpr.files[0].libraryfile, dest_file)
            process = subprocess.Popen(
                ['dpkg-deb', '-c', dest], cwd=tmp_dir.path,
                stdout=subprocess.PIPE)
            contents, stderr = process.communicate()
            ret = process.wait()
            if ret != 0:
                return None
            for line in contents.split('\n'):
                # We don't need to care about directories.
                if line.endswith('/'):
                    continue
                if line == '':
                    continue
                split_line = line.split()
                bpp = getUtility(IBinaryPackagePathSource).getOrCreate(
                    unicode(split_line[-1][2:]))
                bprc = BinaryPackageReleaseContents()
                bprc.binarypackagerelease = bpr
                bprc.binarypackagepath = bpp
                store.add(bprc)

    def remove(self, bpr):
        """See `IBinaryPackageReleaseContents`."""
        store = IMasterStore(BinaryPackageReleaseContents)
        results = store.find(
            BinaryPackageReleaseContents,
            BinaryPackageReleaseContents.binarypackagerelease == bpr.id)
        for bprc in results:
            store.remove(bprc)
