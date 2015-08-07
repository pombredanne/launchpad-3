# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap views."""

__metaclass__ = type
__all__ = [
    'SnapNavigation',
    'SnapView',
    ]

from lp.services.webapp import (
    canonical_url,
    LaunchpadView,
    Navigation,
    stepthrough,
    )
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.breadcrumb import (
    Breadcrumb,
    NameBreadcrumb,
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


class SnapBreadcrumb(NameBreadcrumb):

    @property
    def inside(self):
        return Breadcrumb(
            self.context.owner,
            url=canonical_url(self.context.owner, view_name="+snap"),
            text="Snap packages", inside=self.context.owner)


class SnapView(LaunchpadView):
    """Default view of a Snap."""

    @property
    def page_title(self):
        return "%(name)s's %(snap_name)s snap package" % {
            'name': self.context.owner.displayname,
            'snap_name': self.context.name,
            }

    label = page_title

    @property
    def builds(self):
        return builds_for_snap(self.context)


def builds_for_snap(snap):
    """A list of interesting builds.

    All pending builds are shown, as well as 1-10 recent builds.  Recent
    builds are ordered by date finished (if completed) or date_started (if
    date finished is not set due to an error building or other circumstance
    which resulted in the build not being completed).  This allows started
    but unfinished builds to show up in the view but be discarded as more
    recent builds become available.

    Builds that the user does not have permission to see are excluded.
    """
    builds = [
        build for build in snap.pending_builds
        if check_permission('launchpad.View', build)]
    for build in snap.completed_builds:
        if not check_permission('launchpad.View', build):
            continue
        builds.append(build)
        if len(builds) >= 10:
            break
    return builds
