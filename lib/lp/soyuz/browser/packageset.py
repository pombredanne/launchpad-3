# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser views for packagesets."""

__metaclass__ = type

__all__ = [
    'PackagesetSetNavigation',
    ]


from lp.soyuz.interfaces.packageset import IPackagesetSet
from canonical.launchpad.webapp import GetitemNavigation


class PackagesetSetNavigation(GetitemNavigation):
    """Navigation methods for PackagesetSet."""
    usedfor = IPackagesetSet
