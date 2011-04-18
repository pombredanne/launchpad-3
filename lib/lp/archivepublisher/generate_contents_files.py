# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Archive Contents files generator."""

__metaclass__ = type
__all__ = [
    'GenerateContentsFiles',
    ]

from optparse import OptionValueError
import os
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.ftests.script import run_command
from lp.archivepublisher.config import getPubConfig
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )
from lp.services.utils import file_exists
from lp.soyuz.scripts.ftpmaster import LpQueryDistro


COMPONENTS = [
    'main',
    'restricted',
    'universe',
    'multiverse',
    ]


def differ_in_content(one_file, other_file):
    """Do the two named files have different contents?"""
    return file(one_file).read() != file(other_file).read()


class StoreArgument:
    """Local helper for receiving `LpQueryDistro` results."""

    def __call__(self, argument):
        """Store call argument."""
        self.argument = argument


def get_template(template_name):
    """Return path of given template in this script's templates directory."""
    return os.path.join(
        config.root, "cronscripts", "publishing", "gen-contents",
        template_name)


def execute(logger, command_line):
    description = ' '.join(command_line)
    logger.debug("Execute: %s", description)
    retval, stdout, stderr = run_command(command_line)
    logger.debug(stdout)
    logger.warn(stderr)
    if retval != 0:
        raise LaunchpadScriptFailure(
            "Failure while running command: %s" % description)


class GenerateContentsFiles(LaunchpadScript):

    distribution = None

    def add_my_options(self):
        """See `LaunchpadScript`."""
        self.parser.add_option(
            "-d", "--distribution", dest="distribution", default=None,
            help="Distribution to generate Contents files for.")

    @property
    def name(self):
        """See `LaunchpadScript`."""
        if self.distribution is None:
            return self._name
        else:
            return "%s-%s" % (self._name, self.distribution.name)

    def processOptions(self):
        if self.options.distribution is None:
            raise OptionValueError("Specify a distribution.")

        self.distribution = getUtility(IDistributionSet).getByName(
            self.options.distribution)
        if self.distribution is None:
            raise OptionValueError(
                "Distribution '%s' not found." % self.options.distribution)

    def setUpPrivateTree(self):
        self.logger.debug("Ensuring that we have a private tree in place.")
        for suffix in ['cache', 'misc']:
            dirname = '%s-%s' % (self.distribution.name, suffix)
            os.makedirs(os.path.join(self.content_archive, dirname))

    def queryDistro(self, request, options=None):
        """Call the query-distro script about `self.distribution`."""
        args = ['-d', self.distribution.name]
        if options is not None:
            args += options
        args += request
        query_distro = LpQueryDistro(test_args=args)
        receiver = StoreArgument()
        query_distro.runAction(presenter=receiver)
        return receiver.argument

    def getPocketSuffixes(self):
        return self.queryDistro("pocket_suffixes").split()

    def getSuites(self):
        return self.queryDistro("supported").split()

    def getArchs(self):
        devel = self.queryDistro("development")
        return self.queryDistro("archs", options=["-s", devel])

    def getDirs(self, archs):
        return ['source', 'debian-installer'] + [
            'binary-%s' % arch.name for arch in archs]

    def writeAptConf(self, suites, archs):
        output_dirname = '%s-misc' % self.distribution.name
        output_file = file(os.path.join(
            self.content_archive, output_dirname, "apt-contents.conf"))

        parameters = {
            'architectures': archs,
            'content_archive': self.content_archive,
            'distribution': self.distribution.name,
        }

        header = get_template('apt_conf_header.template')
        output_file.write(file(header).read() % parameters)

        dist = get_template('apt_conf_dist.template')
        dist_template = dist.read()

        for suite in suites:
            parameters['suite'] = suite
            output_file.write(dist_template % parameters)

        output_file.close()

    def createComponentDirs(self, suites, archs):
        for suite in suites:
            for component in COMPONENTS:
                for directory in self.getDirs(archs):
                    path = os.path.join(
                        self.content_archive, self.distribution.name, 'dists',
                        suite, component, directory)
                    if not file_exists(path):
                        self.logger.debug("Creating %s", path)
                        os.makedirs(path)

    def writeContentsTop(self):
        output_filename = os.path.join(
            self.content_archive, '%s-misc' % self.distribution.name,
            "Contents.top")
        parameters = {
            'distrotitle': self.distribution.title,
        }
        output_file = file(output_filename, 'w')
        output_file.write(
            file(get_template('Contents.top')).read() % parameters)
        output_file.close()

    def generateContentsFiles(self):
        self.logger.debug(
            "Running apt in private tree to generate new contents.")
        execute(self.logger, [
            "cp",
            "-a",
            self.config.overrideroot,
            "%s/" % self.content_archive,
            ])
        self.writeContentsTop()
        execute(self.logger, [
            "apt-ftparchive",
            "generate",
            "%s/%s-misc/apt-contents.conf" % (
                self.content_archive, self.distribution.name),
            ])

    def installContentsFile(self, suite, arch):
        contents_dir = os.path.join(
            self.content_archive, self.distribution.name, 'dists', suite)
        contents_filename = "Contents-%s" % arch
        last_contents = os.path.join(contents_dir, ".%s" % contents_filename)
        current_contents = os.path.join(contents_dir, contents_filename)

        # Avoid rewriting unchanged files; mirrors would have to
        # re-fetch them unnecessarily.
        if differ_in_content(current_contents, last_contents):
            self.logger.debug(
                "Installing new Contents file for %s/%s", suite, arch)
            if file_exists(last_contents):
                os.remove(last_contents)
            os.rename(current_contents, last_contents)

            new_contents = os.path.join(
                contents_dir, "%s.gz" % contents_filename)
            contents_dest = os.path.join(
                self.config.distsroot, suite, "%s.gz" % contents_filename)
            if file_exists(contents_dest):
                os.remove(contents_dest)
            os.rename(new_contents, contents_dest)
            os.chmod(contents_dest, 0664)
        else:
            self.logger.debug(
                "Skipping unmodified Contents file for %s/%s", suite, arch)

    def compareAndUpdate(self, suites, archs):
        self.logger.debug("Comparing contents files with public tree.")
        for suite in suites:
            for arch in archs:
                self.installContentsFile(suite, arch)

    def main(self):
        self.processOptions()

        self.config = getPubConfig(self.distribution.main_archive)
        self.content_archive = os.path.join(
            config.archivepublisher.content_archive_root,
            self.distribution.name + "-contents")

        self.setUpPrivateTree()
        suites = self.getSuites()
        archs = self.getArchs()
        self.writeAptConf(suites, archs)
        self.createComponentDirs(suites, archs)
        self.generateContentsFiles()
        self.compareAndUpdate(suites, archs)
