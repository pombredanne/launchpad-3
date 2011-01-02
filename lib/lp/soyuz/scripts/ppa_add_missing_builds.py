#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import sys

from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.services.scripts.base import LaunchpadScript
from lp.soyuz.enums import PackagePublishingStatus


class PPAMissingBuilds(LaunchpadScript):
    """Helper class to create builds in PPAs for requested architectures."""

    def add_missing_ppa_builds(self, ppa, required_arches, distroseries):
        """For a PPA, create builds as necessary.

        :param ppa: The PPA
        :param required_arches: A list of `DistroArchSeries`
        :param distroseries: The context `DistroSeries` in which to create
            builds.
        """
        # Listify the architectures to avoid hitting this MultipleJoin
        # multiple times.
        distroseries_architectures = list(distroseries.architectures)
        if not distroseries_architectures:
            self.logger.error(
                "No architectures defined for %s, skipping"
                % distroseries.name)
            return

        architectures_available = set(distroseries.buildable_architectures)
        if not architectures_available:
            self.logger.error(
                "Chroots missing for %s" % distroseries.name)
            return

        self.logger.info(
            "Supported architectures in %s: %s" % (
                distroseries.name,
                ", ".join(arch_series.architecturetag
                         for arch_series in architectures_available)))

        required_arch_set = set(required_arches)
        doable_arch_set = architectures_available.intersection(
            required_arch_set)
        if len(doable_arch_set) == 0:
            self.logger.error("Requested architectures not available")
            return

        sources = ppa.getPublishedSources(
            distroseries=distroseries,
            status=PackagePublishingStatus.PUBLISHED)
        if not sources.count():
            self.logger.info("No sources published, nothing to do.")
            return

        self.logger.info("Creating builds in %s" %
                 " ".join(arch_series.architecturetag
                          for arch_series in doable_arch_set))
        for pubrec in sources:
            self.logger.info("Considering %s" % pubrec.displayname)
            builds = pubrec.createMissingBuilds(
                architectures_available=doable_arch_set, logger=self.logger)
            if len(builds) > 0:
                self.logger.info("Created %s build(s)" % len(builds))

    def add_my_options(self):
        """Command line options for this script."""
        self.parser.add_option(
            "-a", action="append", dest='arch_tags', default=[])
        self.parser.add_option("-s", action="store", dest='distroseries_name')
        self.parser.add_option(
            "-d", action="store", dest='distribution_name', default="ubuntu")
        self.parser.add_option(
            "--owner", action="store", dest='ppa_owner_name')
        self.parser.add_option(
            "--ppa", action="store", dest='ppa_name', default="ppa")

    def main(self):
        """Entry point for `LaunchpadScript`s."""
        if not self.options.arch_tags:
            self.parser.error("Specify at least one architecture.")

        if not self.options.distroseries_name:
            self.parser.error("Specify a distroseries.")

        if not self.options.ppa_owner_name:
            self.parser.error("Specify a PPA owner name.")

        # Avoid circular imports by importing here.
        from lp.registry.interfaces.distribution import IDistributionSet
        distro = getUtility(IDistributionSet).getByName(
            self.options.distribution_name)
        if distro is None:
            self.parser.error("%s not found" % self.options.distribution_name)

        try:
            distroseries = distro.getSeries(self.options.distroseries_name)
        except NotFoundError:
            self.parser.error("%s not found" % self.options.distroseries_name)

        arches = []
        for arch_tag in self.options.arch_tags:
            try:
                das = distroseries.getDistroArchSeries(arch_tag)
                arches.append(das)
            except NotFoundError:
                self.parser.error(
                    "%s not a valid architecture for %s" % (
                        arch_tag, self.options.distroseries_name))

        from lp.registry.interfaces.person import IPersonSet
        owner = getUtility(IPersonSet).getByName(self.options.ppa_owner_name)
        if owner is None:
            self.parser.error("%s not found" % self.options.ppa_owner_name)

        try:
            ppa = owner.getPPAByName(self.options.ppa_name)
        except NotFoundError:
            self.parser.error("%s not found" % self.options.ppa_name)

        # I'm tired of parsing options.  Let's do it.
        try:
            self.add_missing_ppa_builds(ppa, arches, distroseries)
            self.txn.commit()
            self.logger.info("Finished adding builds.")
        except Exception, err:
            self.logger.error(err)
            self.txn.abort()
            self.logger.info("Errors, aborted transaction.")
            sys.exit(1)


