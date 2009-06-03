# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser views for packagesets."""

__metaclass__ = type

__all__ = [
    'PackagesetSetNavigation',
    ]


from canonical.launchpad.webapp import GetitemNavigation
from lp.soyuz.interfaces.packageset import IPackagesetSet


class PackagesetSetNavigation(GetitemNavigation):
    """Navigation methods for PackagesetSet."""
    usedfor = IPackagesetSet
