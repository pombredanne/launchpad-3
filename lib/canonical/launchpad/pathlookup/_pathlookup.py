# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""This module contains functions related to path lookup.

XXX: All functions are taken from banzai.backend.lp, and modifed to
     function within launchpad, and be more launchpad specific. The rest
     of banzai.backend.lp should be moved as well. All of
     banzai.backend.lp should be moved to launchpad.
     -- Bjorn Tillenius, 2005-05-19
"""

__metaclass__ = type
__all__ = ['get_object']

import urlparse
    
from sqlobject import SQLObjectNotFound

from zope.component import getUtility
from zope.exceptions import NotFoundError
    
from canonical.launchpad.pathlookup.exceptions import (
    PathLookupError, PathStepNotFoundError, PathStepRequiredError)
from canonical.launchpad.interfaces import (
    IProduct, IDistribution, IProductSeries, IProductRelease, IDistroRelease,
    ISourcePackageName, ISourcePackage, ISourcePackageRelease, IProductSet, 
    IDistributionSet, ISourcePackageNameSet, IDistroReleaseSet,
    ILaunchpadCelebrities
    )

# URL schemes we handle
SCHEMES = ("lp", "launchpad")
urlparse.uses_netloc.append("lp")
urlparse.uses_netloc.append("launchpad")


def split_path(url_path):
    """Return the parts of the URL path after canonicalisation.

    Canonicalises the URL path by removing empty parts, /./ and resolving
    /../  etc.  Then splits it and returns the parts as a list.
    """
    parts = []
    for part in url_path.split("/"):
        if not len(part):
            continue
        elif part == ".":
            continue
        elif part == "..":
            if len(parts):
                parts.pop()
        else:
            parts.append(part)

    return parts


# XXX: I should convert the tests in banzai.backend.lp to a nice system
#      documentation test
#      -- Bjorn Tillenius, 2005-06-31
def get_object(url_or_path, default_distro=None, path_only=False):
    """Return database object at the given path.

    This function returns the database object actually referenced by the
    path, i.e. the Product, ProductSeries, Distro, etc.
    Returns SQLBase record object.

    See banzai/backend/lp.py for more information. 

    Three exception can be raised, PathLookupError,
    PathStepRequiredError, and PathStepNotFoundError. The two latter
    extend the former.

    PathStepRequiredError is raised when a certain part of the part is
    missing, for example '/products' is missing a product. 

    PathStepNotFoundError is raised when a part of the part can't be
    found. For example if 'foo' isn't a product and '/products/foo' is
    given.
    """
    if default_distro is None:
        default_distro = getUtility(ILaunchpadCelebrities).ubuntu

    if path_only:
        path = url_or_path
    else:
        (scheme, netloc, path, query, fragment) = urlparse.urlsplit(
            url_or_path, SCHEMES[0])

    parts = split_path(path)
    if not len(parts):
        raise PathLookupError(
            "Malformed URL, path expected: '%s'" % url_or_path)

    obj = None
    while len(parts):
        part = parts.pop(0)

        if obj is None:
            # The first part of a path can be either an explicit starting
            # point in the schema (products or distros) or the name of
            # anything else.  Check for the former first, then go through
            # the tables in precedence order looking for the records.
            if part == "products" or part == "upstream":
                try:
                    product = parts.pop(0)
                except IndexError:
                    raise PathStepRequiredError(
                        "Product missing in: '%s'" % url_or_path, IProduct)
                productset = getUtility(IProductSet)
                try:
                    obj = productset[product]
                except NotFoundError:
                    raise PathStepNotFoundError(
                        "Product '%s' not found in: '%s'" % (
                            product, url_or_path),
                        product, IProduct)

            elif part == "distros":
                try:
                    distro = parts.pop(0)
                except IndexError:
                    raise PathStepRequiredError(
                        "Distribution missing in: '%s'" % url_or_path,
                        IDistribution)
                distroset = getUtility(IDistributionSet)
                try:
                    obj = distroset[distro]
                except NotFoundError:
                    raise PathStepNotFoundError(
                        "Distribution '%s' not found in: '%s'" % (
                            distro, url_or_path),
                        distro, IDistribution)
            else:
                distroset = getUtility(IDistributionSet)
                try:
                    obj = distroset[part]
                    continue
                except NotFoundError:
                    pass

                objs = getUtility(IDistroReleaseSet).findByName(part)
                if objs.count() == 1:
                    obj = objs[0]
                    continue

                objs = getUtility(IDistroReleaseSet).findByVersion(part)
                if objs.count() == 1:
                    obj = objs[0]
                    continue

                sourcepackagenameset = getUtility(ISourcePackageNameSet)

                try:
                    name = sourcepackagenameset[part]
                    # FIXME "current" distro?
                    distro = default_distro
                    obj = distro.getSourcePackage(name)
                    continue
                # XXX: Which exception can getSourcePackage raise?
                #      -- Bjorn Tillenius, 2005-05-19
                except NotFoundError:
                    pass
                except SQLObjectNotFound:
                    pass
                except IndexError:
                    pass

                productset = getUtility(IProductSet)
                try:
                    obj = productset[part]
                    continue
                except NotFoundError:
                    pass

                raise PathLookupError("Path not found in: '%s'" % url_or_path)

        elif IProduct.providedBy(obj):
            # The part of a URL after a product can be either a release
            # version or a series name, check series first as that's less
            # specific and you can always specify /2.0/2.0 to get to the
            # release.
            try:
                obj = obj.getSeries(part)
            except NotFoundError:
                try:
                    obj = obj.getRelease(part)
                except IndexError:
                    # XXX: When banzai is changed to use this function,
                    #      getRelease should be changed to raise
                    #      NotFoundError instead.
                    #      -- Bjorn Tillenius, 2005-05-19
                    raise PathStepNotFoundError(
                        "Product series or release '%s' not found in: '%s'" % (
                            part, url_or_path),
                        part, IProductSeries, IProductRelease)

        elif IProductSeries.providedBy(obj):
            # The part of a URL after a product series is always a release
            # version.
            try:
                obj = obj.getRelease(part)
            except NotFoundError:
                raise PathStepNotFoundError(
                    "Release '%s' not found in: '%s'" % (
                        part, url_or_path),
                    part, IProductRelease)

        elif IProductRelease.providedBy(obj):
            # Nothing is permitted after a release version.
            raise PathLookupError(
                "Malformed path, nothing expected after release: '%s'" %
                url_or_path)

        elif IDistribution.providedBy(obj):
            # The part of a URL after a distribution can be either a release
            # name or a source package name, check release name first as that's
            # less specific.
            try:
                obj = obj.getRelease(part)
                continue
            except NotFoundError:
                pass

            sourcepackagenameset = getUtility(ISourcePackageNameSet)
            try:
                name = sourcepackagenameset[part]
                obj = obj.getSourcePackage(name)
                continue
            # XXX: Which exception can getSourcePackage raise?
            #      -- Bjorn Tillenius, 2005-05-19
            except NotFoundError:
                pass
            except SQLObjectNotFound:
                pass
            except IndexError:
                pass

            raise PathStepNotFoundError(
                "Distribution release or source package '%s'"
                " not found in: '%s'" % (part, url_or_path),
                part, IDistroRelease, ISourcePackageName)

        elif IDistroRelease.providedBy(obj):
            # The part of a URL after a distribution release is always a
            # source package name, for which the currently published version
            # is returned.  A +sources part is optional for compatibility
            # with the Launchpad webapp URLs.
            if part == "+sources":
                if len(parts):
                    part = parts.pop(0)
                else:
                    continue

            sourcepackagenameset = getUtility(ISourcePackageNameSet)
            try:
                name = sourcepackagenameset[part]
            except NotFoundError:
                raise PathStepNotFoundError(
                    "Source package '%s' not found in: '%s'" % (
                        part, url_or_path),
                    part, ISourcePackageName)

            objs = obj.getPublishedReleases(name)
            if len(objs) < 1:
                raise PathLookupError(
                    "Source package '%s' not released in: '%s'" % (
                        part, url_or_path))

            spr = objs[-1].sourcepackagerelease
            obj = SourcePackageReleaseInDistroRelease(spr, obj)

        elif ISourcePackage.providedBy(obj):
            # The part of the URL after a source package is always a
            # source package release.  FIXME this should use
            # SourcePackageHistory or similar
            rels = [ _r for _r in obj.releases if _r.version == part ]
            if not len(rels):
                raise PathStepNotFoundError(
                    "Source package release '%s' not found in: '%s'" % (
                        part, url_or_path),
                    part, ISourcePackageRelease)

            obj = SourcePackageReleaseInDistroRelease(rels[-1],
                                                      obj.distrorelease)

        else:
            raise PathLookupError(
                "Malformed path, '%s' unexpected in: '%s'" % (
                    part, url_or_path))

    return obj
