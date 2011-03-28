# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Master distro publishing script."""

__metaclass__ = type
__all__ = [
    'PublishFTPMaster',
    ]

from optparse import OptionParser
import os
import subprocess
from zope.component import getUtility

from canonical.config import config
from lp.archivepublisher.config import getPubConfig
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.scripts.base import (
    LaunchpadCronScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.scripts import publishdistro
from lp.soyuz.scripts.ftpmaster import LpQueryDistro
from lp.soyuz.scripts.processaccepted import ProcessAccepted


ARCHIVES_TO_PUBLISH = [
    ArchivePurpose.PRIMARY,
    ArchivePurpose.PARTNER,
    ]


ARCHIVE_SUFFIXES = {
    ArchivePurpose.PRIMARY: "",
    ArchivePurpose.PARTNER: "-partner",
}


def file_exists(path):
    """Does `path` represent an existing file?"""
    return os.access(path, os.F_OK)


def run_command(args):
    """Run command line (passed as a list).

    :return: A tuple of process return value; stdout; and stderr.
    """
    child = subprocess.Popen(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = child.communicate()
    result = child.wait()
    return (result, stdout, stderr)


def get_distscopyroot(archive_config):
    """Return the distscropy root directory for `archive_config`."""
    return archive_config.archiveroot + "-distscopy"


class StoreArgument:
    """Helper class: receive argument and store it."""

    def __call__(self, argument):
        self.argument = argument


class PublishFTPMaster(LaunchpadCronScript):
    """."""

    done_pub = False

    def add_my_options(self):
        self.parser.add_option(
            '-d', '--distribution', dest='distribution', default=None,
            help="Distribution to publish.")
        self.parser.add_option(
            '-s', '--security-only', dest='security_only',
            action='store_true', default=False, help="Security upload only.")

    def getArchives(self):
        """Find archives for `self.distribution` that should be published."""
        return [
            archive
            for archive in self.distribution.all_distro_archives
                if archive.purpose in ARCHIVES_TO_PUBLISH]

    def makeConfigs(self):
        """Set up configuration objects for archives to be published.

        The configs dict maps the archive purposes that are relevant for
        publishing to the respective archives' configurations.
        """
        return dict(
            (archive.purpose, getPubConfig(archive))
            for archive in self.archives)

    def cleanUp(self):
        for purpose, archive_config in self.configs.iteritems():
            self.logger.debug(
                "Moving %s dists backup to safe keeping for next time.",
                purpose.title)
            distscopyroot = archive_config.archiveroot + '-distscopy'
            dists = os.path.join(distscopyroot, "dists")
            if self.done_pub:
                replacement_dists = archive_config.distsroot + ".old"
            else:
                replacement_dists = archive_config.distsroot + ".new"
            if file_exists(replacement_dists):
                os.rename(replacement_dists, dists)

    def processAccepted(self):
        self.logger.debug(
            "Processing the accepted queue into the publishing records...")
        script = ProcessAccepted(test_args=[self.distribution.name])
        script.txn = self.txn
        script.logger = self.logger
        script.main()

    def getDirtySuites(self):
        """Return list of suites that have packages pending publication."""
        self.logger.debug("Querying which suites are pending publication...")
        query_distro = LpQueryDistro(
            test_args=['-d', self.distribution.name, "pending_suites"])
        receiver = StoreArgument()
        query_distro.runAction(presenter=receiver)
        return receiver.argument

    def gatherSecuritySuites(self):
        """List security suites."""
        suites = self.getDirtySuites()
        return [suite for suite in suites if suite.endswith('-security')]

    def rsync(self, source_dir, dest_dir, archive_purpose):
        """Update the contents of `dest_dir` based on those of `source_dir`.

        Uses "rsync -aH --delete".

        :param source_dir: Source directory.  Its contents will be
            copied, but not the directory itself.
        :param dest_dir: Destiantion directory.  Its contents will be
            updated.
        :param archive_purpose: The `ArchivePurpose` of the archive
            whose contents are being synchronized.
        """
        archive_config = self.configs[archive_purpose]

        # The --delete is needed to ensure that we don't accidentally
        # resurrect files that were meant to be deleted (bug 58835).
        retval, stdout, stderr = run_command([
            "rsync",
            "-aH",
            "--delete",
            archive_config.distsroot + "/",
            os.path.join(archive_config.archiveroot, "dists.new"),
            ])

        if retval != 0:
            self.logger.warn(stdout)
            self.logger.error(stderr)
            raise LaunchpadScriptFailure(
                "Failed to rsync dists.new for %s." % archive_purpose.title)

    def setUpDirs(self):
        """Copy the dists tree ready for publishing into.

        We do this so that we don't get an inconsistent dists tree at
        any point during the publishing cycle (which would cause buildds
        to explode).

        This is now done through maintaining a persistent backup copy of
        the dists directory, which we move into place and bring up to
        date with rsync.  Should achieve the same effect as copying, but
        faster.
        """
        for archive_config in self.configs.itervalues():
            archiveroot = archive_config.archiveroot
            if not file_exists(archiveroot):
                self.logger.debug("Creating archive root %s.", archiveroot)
                os.makedirs(archiveroot)
            distsroot = archive_config.distsroot
            if not file_exists(distsroot):
                self.logger.debug("Creating dists root %s.", distsroot)
                os.makedirs(distsroot)

        for purpose, archive_config in self.configs.iteritems():
            dists = os.path.join(get_distscopyroot(archive_config), "dists")
            dists_new = os.path.join(archive_config.archiveroot, "dists.new")
            if not file_exists(dists):
                os.makedirs(dists)
            os.rename(dists, dists_new)
            self.rsync(archive_config.distsroot, dists_new, purpose)

    def publishDistro(self, archive, security_suites=None):
        """Publish the results for an archive.

        :param archive: Archive to publish.
        :param security_suites: An optional list of suites to restrict
            the publishing to.
        """
        purpose = archive.purpose
        self.logger.debug(
            "Publishing the %s %s...", self.distribution.name, purpose.title)
        archive_config = self.configs[purpose]
        arguments = [
            '-v', '-v',
            '-d', self.distribution.name,
            '-R', archive_config.distsroot + '.new',
            ]

        if archive.purpose == ArchivePurpose.PARTNER:
            arguments.append('--partner')

        if security_suites is not None:
            arguments += sum([['-s', suite] for suite in security_suites], [])

        parser = OptionParser()
        publishdistro.add_options(parser)
        options, args = parser.parse_args(arguments)
        publishdistro.run_publisher(options, txn=self.txn, log=self.logger)

        self.runPublishDistroParts(archive)

    def runPublishDistroParts(self, archive):
        """Execute the publish-distro hooks."""
        archive_config = self.configs[archive.purpose]
        env = {
            'DISTSROOT': archive_config.distsroot,
            'ARCHIVEROOT': archive_config.archiveroot,
            }
        self.runParts('publish-distro.d', env)

    def installDists(self):
        """Put the new dists into place, as near-atomically as possible."""
        self.logger.debug("Placing the new dists into place...")

        for archive_config in self.configs.itervalues():
            distsroot = archive_config.distsroot
            os.rename(distsroot, distsroot + ".old")
            os.rename(distsroot + ".new", distsroot)

        self.done_pub = True

        for archive_config in self.configs.itervalues():
            dists = os.path.join(get_distscopyroot(archive_config), "dists")
            os.rename(archive_config.distsroot + ".old", dists)

    def runCommercialCompat(self):
        """Generate the -commercial pocket.

        This is done for backwards compatibility with dapper, edgy, and
        feisty releases.  Failure here is not fatal.
        """
        # XXX JeroenVermeulen 2011-03-24 bug=741683: Retire
        # commercial-compat.sh (and this method) as soon as Dapper
        # support ends.
        if self.distribution.name != 'ubuntu':
            return
        if config.instance_name != 'production':
            return

        try:
            os.system("""
                env PATH="$PATH:%s/cronscripts/publishing" \
                    LPCONFIG="%s" \
                    commercial-compat.sh
                """ % (config.root, config.instance_name))
        except Exception:
            pass

    def generateListings(self):
        """Create ls-lR.gz listings."""
        self.logger.debug("Creating ls-lR.gz...")
        lslr = "ls-lR.gz"
        lslr_new = "." + lslr + ".new"
        for purpose, archive_config in self.configs.iteritems():
            lslr_file = os.path.join(archive_config.archiveroot, lslr)
            new_lslr_file = os.path.join(archive_config.archiveroot, lslr_new)
            if file_exists(new_lslr_file):
                os.remove(new_lslr_file)
            retval = os.system(
                "cd -- '%s' ; TZ=UTC ls -lR | gzip -9n >'%s'"
                % (archive_config.archiveroot, lslr_new))
            if retval != 0:
                raise LaunchpadScriptFailure(
                    "Failed to create %s for %s." % (lslr, purpose.title))
            os.rename(new_lslr_file, lslr_file)

    def clearEmptyDirs(self):
        """Clear out any redundant empty directories."""
        for archive_config in self.configs.itervalues():
            os.system(
                "find '%s' -type d -empty | xargs -r rmdir"
                % archive_config.archiveroot)

    def processOptions(self):
        """Handle command-line options.

        Sets `self.distribution` to the `Distribution` to publish.
        """
        if self.options.distribution is None:
            raise LaunchpadScriptFailure("Specify a distribution.")

        self.distribution = getUtility(IDistributionSet).getByName(
            self.options.distribution)
        if self.distribution is None:
            raise LaunchpadScriptFailure(
                "Distribution %s not found." % self.options.distribution)

    def runParts(self, parts, env):
        """Execute run-parts.

        :param parts: The run-parts directory to execute:
            "publish-distro.d" or "finalize.d".
        :param env: A dict of environment variables to pass to the
            scripts in the run-parts directory.
        """
        parts_dir = os.path.join(
            config.root, 'cronscripts', 'publishing', 'distro-parts',
            config.instance_name, self.distribution.name, parts)
        if not file_exists(parts_dir):
            return
        env_string = ' '.join(['='.join(pair for pair in env.iteritems())])
        retval = os.system("%s run-parts -- '%s'" % (env_string, parts_dir))
        if retval != 0:
            raise LaunchpadScriptFailure(
                "Failure while executing run-parts %s." % parts_dir)

    def runFinalizeParts(self, security_only=False):
        """Run the finalize.d parts to finalize publication."""
        boolean_text = {
            True: "yes",
            False: "no",
        }
        env = {'SECURITY_UPLOAD_ONLY': boolean_text[security_only]}
        self.runParts('finalize.d', env)

    def publishSecurityUploads(self):
        security_suites = self.gatherSecuritySuites()
        if len(security_suites) == 0:
            self.logger.info("Nothing to do for security publisher.")
            return
        partner_archive = self.distribution.getArchive("partner")
        if partner_archive is not None:
            self.publishDistro(partner_archive)
        self.publishDistro(
            self.distribution.main_archive, security_suites=security_suites)
        self.installDists()
        self.runCommercialCompat()
        self.runFinalizeParts(security_only=True)

    def publishAllUploads(self):
        for archive in self.archives:
            # This, for the main archive, is where the script spends
            # most of its time.
            self.publishDistro(archive)

        self.installDists()
        self.runCommercialCompat()
        self.generateListings()
        self.clearEmptyDirs()
        self.runFinalizeParts()

    def main(self):
        self.processOptions()
        self.archives = self.getArchives()
        self.configs = self.makeConfigs()

        try:
            self.processAccepted()
            # XXX: Repeat setUpDirs for security/full upload?
            self.setUpDirs()
            self.publishSecurityUploads()
            if not self.options.security_only:
                self.publishAllUploads()
        finally:
            self.cleanUp()
