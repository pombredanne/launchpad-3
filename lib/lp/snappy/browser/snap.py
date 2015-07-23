# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap views."""

__metaclass__ = type
__all__ = [
    'SnapNavigation',
    ]

from lp.services.webapp import (
    Navigation,
    stepthrough,
    )
from lp.snappy.interfaces.snap import ISnap
from lp.snappy.interfaces.snapbuild import ISnapBuildSet
from lp.soyuz.browser.build import get_build_by_id_str


class SnapNavigation(Navigation):
    usedfor = ISnap

    @stepthrough('+build')
    def traverse_build(self, name):
        build = get_build_by_id_str(ISnapBuildSet, name)
        if build is None or build.snap != self.context:
            return None
        return build
