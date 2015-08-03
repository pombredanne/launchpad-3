# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SnapBuild views."""

__metaclass__ = type
__all__ = [
    'SnapBuildNavigation',
    ]

from lp.services.librarian.browser import FileNavigationMixin
from lp.services.webapp import Navigation
from lp.snappy.interfaces.snapbuild import ISnapBuild


class SnapBuildNavigation(Navigation, FileNavigationMixin):
    usedfor = ISnapBuild
