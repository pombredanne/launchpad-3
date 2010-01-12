#!/usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

import _pythonpath

from optparse import OptionParser

from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger)
from canonical.launchpad.webappp.interfaces import NotFoundError
from canonical.lp import initZopeless
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.scripts.base import LaunchpadScriptFailure

def add_missing_ppa_builds(ppa, required_arches, distroseries):
    # Listify the architectures to avoid hitting this MultipleJoin
    # multiple times.
    distroseries_architectures = list(distroseries.architectures)
    if not distroseries_architectures:
        log.error(
            "No architectures defined for %s, skipping"
            % distroseries.name)
        return

    architectures_available = list(distroseries.enabled_architectures)
    if not architectures_available:
        log.error(
            "Chroots missing for %s, skipping" % distroseries.name)
        return

    log.info(
        "Supported architectures: %s" %
        " ".join(arch_series.architecturetag
                 for arch_series in architectures_available))

    available_arch_set = set(architectures_available)
    required_arch_set = set(required_arches)
    doable_arch_set = available_arch_set.intersection(required_arch_set)
    if len(doable_arch_set) == 0:
        log.error("Requested architectures not available")
        return

    sources = ppa.getPublishedSources(distroseries=distroseries)

    for pubrec in sources:
        builds = pubrec.createMissingBuilds(
            architectures_available=doable_arch_set, logger=log)
        if len(builds) > 0:
            txn.commit()


if __name__ == "__main__":
    parser = OptionParser()

    parser.add_option("-a", action="append", dest=arch_tags)
    parser.add_option("-s", action="store", dest=distroseries_name)
    parser.add_option(
        "-d", action="store", dest=distribution_name, default="ubuntu")
    parser.add_option("--owner", action="store", dest=ppa_owner_name)
    parser.add_option("--ppa", action="store", dest=ppa_name, default="ppa")
    options, args = parser.parse_args()

    if not options.arch_tags:
        parser.error("Specify at least one architecture.")

    if not options.distroseries_name:
        parser.error("Specifiy a distroseries.")

    if not options.ppa_owner_name:
        parser.error("Specify a PPA owner name.")

    log = logger(options, "ppa-add-missing-builds")
    log.debug("Initialising zopeless.")
    execute_zcml_for_scripts()
    txn = initZopeless(dbuser=config.builddmaster.dbuser)

    distro = getUtility(IDistributionSet).getByName(distribution_name)
    if distro is None:
        parser.error("%s not found" % distribution_name)

    try:
        distroseries = distro.getSeries(distroseries_name)
    except NotFoundError:
        parser.error("%s not found" % distroseries_name)

    arches = []
    for arch_tag in arch_tags:
        try:
            das = distroseries.getDistroArchSeries(arch_tag)
            arches.append(das)
        except NotFoundError:
            parser.error(
                "%s not a valid architecture for %s" % (
                    arch_tag, distroseries_name))

    owner = getUtility(IPersonSet).getByName(ppa_owner_name)
    if owner is None:
        parser.error("%s not found" % ppa_owner_name)

    try:
        ppa = owner.getPPAByName(ppa_name)
    except NotFoundError:
        parser.error("%s not found" % ppa_name)

    # I'm tired of parsing options.  Let's do it.
    try:
        add_missing_ppa_builds(ppa, arches, distroseries);
    except LaunchpadScriptFailure, err:
        log.error(err)
