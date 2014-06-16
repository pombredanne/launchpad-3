# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LiveFSNavigation',
    ]

from lp.services.webapp import (
    Navigation,
    stepthrough,
    )
from lp.soyuz.browser.build import get_build_by_id_str
from lp.soyuz.interfaces.livefs import ILiveFS
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuildSet


class LiveFSNavigation(Navigation):
    usedfor = ILiveFS

    @stepthrough('+build')
    def traverse_build(self, name):
        build = get_build_by_id_str(ILiveFSBuildSet, name)
        if build is None or build.livefs != self.context:
            return None
        return build
