# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""All the interfaces that are exposed through the webservice.

There is a declaration in ZCML somewhere that looks like:
  <webservice:register module="lp.snappy.interfaces.webservice" />

which tells `lazr.restful` that it should look for webservice exports here.
"""

__all__ = [
    'ISnap',
    'ISnapBuild',
    'ISnapSet',
    ]

from lp.services.webservice.apihelpers import (
    patch_collection_property,
    patch_entry_return_type,
    patch_reference_property,
    )
from lp.snappy.interfaces.hassnaps import IHasSnaps
from lp.snappy.interfaces.snap import (
    ISnap,
    ISnapSet,
    ISnapView,
    )
from lp.snappy.interfaces.snapbuild import (
    ISnapBuild,
    ISnapFile,
    )


# IHasSnaps
patch_collection_property(IHasSnaps, 'snaps', ISnap)

# ISnapFile
patch_reference_property(ISnapFile, 'snapbuild', ISnapBuild)

# ISnapView
patch_entry_return_type(ISnapView, 'requestBuild', ISnapBuild)
patch_collection_property(ISnapView, 'builds', ISnapBuild)
patch_collection_property(ISnapView, 'completed_builds', ISnapBuild)
patch_collection_property(ISnapView, 'pending_builds', ISnapBuild)
