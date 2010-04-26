# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""URLs for PackageBuild classes."""

from zope.interface import implements

from canonical.launchpad.webapp.interfaces import ICanonicalUrlData


class PackageBuildUrl:
    """Dynamic URL declaration for IPackageBuild classes.

    When dealing with distribution builds we want to present them
    under IDistributionSourcePackageRelease url:

       /ubuntu/+source/foo/1.0/+build/1234

    On the other hand, PPA builds will be presented under the PPA page:

       /~cprov/+archive/+build/1235

    Copy archives will be presented under the archives page:
       /ubuntu/+archive/my-special-archive/+build/1234
    """
    implements(ICanonicalUrlData)
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def inside(self):
        if self.context.archive.is_ppa or self.context.archive.is_copy:
            return self.context.archive
        else:
            return self.context.distributionsourcepackagerelease

    @property
    def path(self):
        return u"+build/%d" % self.context.build_farm_job.id

