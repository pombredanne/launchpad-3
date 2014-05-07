# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LiveFSNavigation',
    'LiveFSSetNavigation',
    ]

from zope.component import getUtility

from lp.services.webapp import (
    canonical_url,
    Navigation,
    stepthrough,
    )
from lp.soyuz.browser.build import get_build_by_id_str
from lp.soyuz.interfaces.livefs import (
    ILiveFS,
    ILiveFSSet,
    )
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuildSet


class LiveFSNavigation(Navigation):
    usedfor = ILiveFS

    @stepthrough('+livefsbuild')
    def traverse_livefsbuild(self, name):
        build = get_build_by_id_str(ILiveFSBuildSet, name)
        if build is None or build.livefs != self.context:
            return None
        return build


class LiveFSSetNavigation(Navigation):
    """Navigation for LiveFSSet.

    This handles URI fragments of the following form:

        /livefses/owner/distribution/distroseries/livefs

    This is of limited usefulness as LiveFSes can be navigated to via
    Person:+livefs, but we need something minimal here to allow the
    "livefses" API root collection to work.
    """
    usedfor = ILiveFSSet

    def traverse(self, owner_name):
        if len(self.request.stepstogo) < 3:
            return None

        distribution_name = self.request.stepstogo.consume()
        distroseries_name = self.request.stepstogo.consume()
        livefs_name = self.request.stepstogo.consume()
        livefs = getUtility(ILiveFSSet).interpret(
            owner_name, distribution_name, distroseries_name, livefs_name)
        return self.redirectSubTree(canonical_url(livefs), status=301)
