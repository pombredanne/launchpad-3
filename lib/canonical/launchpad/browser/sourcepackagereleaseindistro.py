# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['SourcePackageInDistroSetNavigation']

from canonical.launchpad.webapp import GetitemNavigation
from canonical.launchpad.interfaces import ISourcePackageInDistroSet


class SourcePackageInDistroSetNavigation(GetitemNavigation):

    usedfor = ISourcePackageInDistroSet

