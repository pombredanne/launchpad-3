# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageReleaseNavigation',
    'DistributionSourcePackageReleaseView',
    ]

import operator

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.launchpad.webapp import (
    LaunchpadView, Navigation, stepthrough)
from lp.soyuz.interfaces.build import IBuildSet
from lp.soyuz.interfaces.distributionsourcepackagerelease import (
    IDistributionSourcePackageRelease)
from lp.soyuz.interfaces.publishing import PackagePublishingStatus


class DistributionSourcePackageReleaseNavigation(Navigation):
    usedfor = IDistributionSourcePackageRelease

    @stepthrough('+build')
    def traverse_build(self, name):
        try:
            build_id = int(name)
        except ValueError:
            return None
        try:
            return getUtility(IBuildSet).getByBuildID(build_id)
        except NotFoundError:
            return None


class DistroSeriesBuilds:

    def __init__(self, series, builds):
        self.series = series
        self.builds = [
            build
            for build in builds
            if build.distroseries == self.series]


class DistributionSourcePackageReleaseView(LaunchpadView):
    usedfor = IDistributionSourcePackageRelease

    @property
    def page_title(self):
        return self.context.title

    @cachedproperty
    def currently_published(self):
        published_records = [
            publishing for publishing in self.context.publishing_history
            if publishing.status == PackagePublishingStatus.PUBLISHED
            ]
        return list(published_records)

    @property
    def files(self):
        last_publication = self.currently_published[0]
        return [
            ProxiedLibraryFileAlias(
                source_file.libraryfile, last_publication.archive)
            for source_file in self.context.files]

    @cachedproperty
    def sponsor(self):
        upload = self.context.package_upload
        if upload is None:
            return None
        signing_key = upload.signing_key
        if signing_key is None:
            return None
        if signing_key.owner.id == self.context.creator.id:
            return None
        return signing_key.owner

    @cachedproperty
    def grouped_builds(self):
        cached_builds = sorted(
            self.context.builds, key=operator.attrgetter('arch_tag'))
        series = set(
            build.distroseries for build in cached_builds)
        sorted_series = sorted(
            series, key=operator.attrgetter('version'), reverse=True)
        return [
            DistroSeriesBuilds(series, cached_builds)
            for series in sorted_series]
