# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LiveFSBuildNavigation',
    ]

from lp.services.librarian.browser import FileNavigationMixin
from lp.services.webapp import Navigation
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuild


class LiveFSBuildNavigation(Navigation, FileNavigationMixin):
    usedfor = ILiveFSBuild
