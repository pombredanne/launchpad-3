# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate extra overrides using Germinate."""

__metaclass__ = type
__all__ = [
    'GenerateExtraOverrides',
    ]

import os
import logging

from germinate.germinator import Germinator
from germinate.archive import TagFile
from germinate.log import GerminateFormatter
from germinate.seeds import SeedStructure

from zope.component import getUtility

from canonical.launchpad.webapp.dbpolicy import (
    DatabaseBlockedPolicy,
    SlaveOnlyDatabasePolicy,
    )
from lp.app.errors import NotFoundError
from lp.archivepublisher.config import getPubConfig
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.series import SeriesStatus
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.enums import ArchivePurpose


class AtomicFile:
    """Facilitate atomic writing of files."""

    def __init__(self, filename):
        self.filename = filename
        self.fd = open('%s.new' % self.filename, 'w')

    def __enter__(self):
        return self.fd

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.fd.close()
        os.rename('%s.new' % self.filename, self.filename)


class GenerateExtraOverrides(LaunchpadScript):
    """Main class for scripts/ftpmaster-tools/generate-task-overrides.py."""

    def add_my_options(self):
        """Add a 'distribution' context option."""
        self.parser.add_option(
            '-d', '--distribution', dest='distribution_name',
            default='ubuntu', help='Context distribution name.')

    @property
    def name(self):
        """See `LaunchpadScript`."""
        # Include distribution name.  Clearer to admins, but also
        # puts runs for different distributions under separate
        # locks so that they can run simultaneously.
        return "%s-%s" % (self._name, self.options.distribution)

    def processOptions(self):
        try:
            self.distribution = getUtility(
                IDistributionSet)[self.options.distribution_name]
        except NotFoundError, err:
            raise LaunchpadScriptFailure(
                "Could not find distribution %s" % err)

        series = None
        wanted_status = (SeriesStatus.DEVELOPMENT,
                         SeriesStatus.FROZEN)
        for status in wanted_status:
            series = self.distribution.getSeriesByStatus(status)
            if series.count() > 0:
                break
        else:
            raise LaunchpadScriptFailure(
                'There is no DEVELOPMENT distroseries for %s' %
                self.options.distribution_name)
        self.series = series[0]

        # Even if DistroSeries.component_names starts including partner, we
        # don't want it; this applies to the primary archive only.
        self.components = [component
                           for component in self.series.component_names
                           if component != 'partner']

    def getConfig(self):
        """Set up a configuration object for this archive."""
        for archive in self.distribution.all_distro_archives:
            # We only work on the primary archive.
            if archive.purpose == ArchivePurpose.PRIMARY:
                return getPubConfig(archive)
        else:
            raise LaunchpadScriptFailure(
                'There is no PRIMARY archive for %s' %
                self.options.distribution_name)

    def setUp(self):
        """Process options, and set up internal state."""
        self.processOptions()
        self.config = self.getConfig()

        self.germinate_logger = logging.getLogger('germinate')
        self.germinate_logger.setLevel(logging.INFO)
        log_file = os.path.join(self.config.germinateroot, 'germinate.output')
        handler = logging.FileHandler(log_file, mode='w')
        handler.setFormatter(GerminateFormatter())
        self.germinate_logger.addHandler(handler)
        self.germinate_logger.propagate = False

        self.seeds = {}
        self.seed_structures = {}

    def outputPath(self, flavour, series_name, arch, base):
        return os.path.join(
            self.config.germinateroot,
            '%s_%s_%s_%s' % (base, flavour, series_name, arch))

    def runGerminate(self, override_file, series_name, arch, flavours):
        germinator = Germinator(arch)

        # Read archive metadata.
        archive = TagFile(
            series_name, self.components, arch,
            'file:/%s' % self.config.archiveroot, cleanup=True)
        germinator.parse_archive(archive)

        for flavour in flavours:
            self.logger.info('Germinating for %s/%s/%s',
                             flavour, series_name, arch)
            # Add this to the germinate log as well so that that can be
            # debugged more easily.  Log a separator line first.
            self.germinate_logger.info('', extra={'progress': True})
            self.germinate_logger.info('Germinating for %s/%s/%s',
                                       flavour, series_name, arch,
                                       extra={'progress': True})

            # Expand dependencies.
            structure = self.seed_structures[flavour]
            germinator.plant_seeds(structure)
            germinator.grow(structure)
            germinator.add_extras(structure)

            # Write output files.

            # The structure file makes it possible to figure out how the
            # other output files relate to each other.
            structure.write(self.outputPath(
                flavour, series_name, arch, 'structure'))

            # "all" and "all.sources" list the full set of binary and source
            # packages respectively for a given flavour/suite/architecture
            # combination.
            all_path = self.outputPath(flavour, series_name, arch, 'all')
            all_sources_path = self.outputPath(
                flavour, series_name, arch, 'all.sources')
            germinator.write_all_list(structure, all_path)
            germinator.write_all_source_list(structure, all_sources_path)

            # Write the dependency-expanded output for each seed.  Several
            # of these are used by archive administration tools, and others
            # are useful for debugging, so it's best to just write them all.
            for seedname in structure.names:
                germinator.write_full_list(
                    structure,
                    self.outputPath(flavour, series_name, arch, seedname),
                    seedname)

            def writeOverrides(seedname, key, value):
                packages = germinator.get_full(structure, seedname)
                for package in sorted(packages):
                    print >>override_file, '%s/%s  %s  %s' % (
                        package, arch, key, value)

            # Generate apt-ftparchive "extra overrides" for Task fields.
            for seedname in structure.names:
                if seedname == 'extra':
                    continue

                task_headers = {}
                with structure[seedname] as seedtext:
                    for line in seedtext:
                        if line.lower().startswith('task-') and ':' in line:
                            key, value = line.split(':', 1)
                            key = key[5:].lower() # e.g. "Task-Name" => "name"
                            task_headers[key] = value.strip()
                if not task_headers:
                    continue

                # Work out the name of the Task to be generated from this
                # seed.  If there is a Task-Name header, it wins; otherwise,
                # seeds with a Task-Per-Derivative header are honoured for
                # all flavours and put in an appropriate namespace, while
                # other seeds are only honoured for the first flavour and
                # have archive-global names.
                if 'name' in task_headers:
                    task = task_headers['name']
                elif 'per-derivative' in task_headers:
                    task = '%s-%s' % (flavour, seedname)
                elif flavour == flavours[0]:
                    task = seedname
                else:
                    continue

                # The list of packages in this task come from this seed plus
                # any other seeds listed in a Task-Seeds header.
                scan_seeds = set([seedname])
                if 'seeds' in task_headers:
                    scan_seeds.update(task_headers['seeds'].split())
                for scan_seed in sorted(scan_seeds):
                    writeOverrides(scan_seed, 'Task', task)

            # Generate apt-ftparchive "extra overrides" for Build-Essential
            # fields.
            if 'build-essential' in structure.names and flavour == flavours[0]:
                writeOverrides('build-essential', 'Build-Essential', 'yes')

    def generateExtraOverrides(self, series_name, series_architectures,
                               flavours, seed_bases=None):
        for flavour in flavours:
            self.seed_structures[flavour] = SeedStructure(
                '%s.%s' % (flavour, series_name), seed_bases=seed_bases)

        override_path = os.path.join(
            self.config.miscroot,
            'more-extra.override.%s.main' % series_name)
        with AtomicFile(override_path) as override_file:
            for arch in series_architectures:
                self.runGerminate(override_file, series_name, arch, flavours)

    def process(self, seed_bases=None):
        """Do the bulk of the work."""
        self.setUp()

        series_name = self.series.name
        series_architectures = [arch.architecturetag
                                for arch in self.series.architectures]

        # This takes a while.  Ensure that we do it without keeping a
        # database transaction open.
        self.txn.commit()
        with DatabaseBlockedPolicy():
            self.generateExtraOverrides(
                series_name, series_architectures, self.args,
                seed_bases=seed_bases)

    def main(self):
        """See `LaunchpadScript`."""
        # This code has no need to alter the database.
        with SlaveOnlyDatabasePolicy():
            self.process()
