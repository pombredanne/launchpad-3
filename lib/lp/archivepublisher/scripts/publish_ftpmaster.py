# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Master distro publishing script."""

__metaclass__ = type
__all__ = [
    'PublishFTPMaster',
    ]

from optparse import OptionParser
import os
from zope.component import getUtility

from canonical.config import config
from lp.archivepublisher.config import getPubConfig
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.scripts.base import (
    LaunchpadCronScript,
    LaunchpadScriptFailure,
    )
from lp.services.utils import file_exists
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.scripts import publishdistro
from lp.soyuz.scripts.ftpmaster import LpQueryDistro
from lp.soyuz.scripts.processaccepted import ProcessAccepted


# XXX JeroenVermeulen 2011-03-31 bug=746229: to start publishing debug
# archives, get rid of this list.
ARCHIVES_TO_PUBLISH = [
    ArchivePurpose.PRIMARY,
    ArchivePurpose.PARTNER,
    ]


def compose_shell_boolean(boolean_value):
    """Represent a boolean value as "yes" or "no"."""
    boolean_text = {
        True: "yes",
        False: "no",
    }
    return boolean_text[boolean_value]


def compose_env_string(env):
    """Turn a dict into a series of shell parameter assignments."""
    return ' '.join(['='.join(pair) for pair in env.iteritems()])


def get_backup_dists(archive_config):
    """Return the path of an archive's backup dists directory."""
    return os.path.join(archive_config.archiveroot + "-distscopy", "dists")


def get_dists(archive_config, suffix=''):
    """Return the path of an archive's dists directory.

    :param archive_config: Configuration for the archive in question.
    :param suffix: An optional suffix for the name of the dists
        directory.  The dists directories are shuffled around between
        dists, dists.new, and dists.old.  This makes it easier to
        specify any one of those paths.
    """
    return archive_config.distsroot + suffix


class StoreArgument:
    """Helper class: receive argument and store it."""

    def __call__(self, argument):
        self.argument = argument


def find_run_parts_dir(distro, parts):
    """Find the requested run-parts directory, if it exists."""
    run_parts_location = config.archivepublisher.run_parts_location
    if not run_parts_location:
        return

    if run_parts_location.startswith("/"):
        # Absolute path.
        base_dir = run_parts_location
    else:
        # Relative path.
        base_dir = os.path.join(config.root, run_parts_location)

    parts_dir = os.path.join(base_dir, distro.name, parts)
    if file_exists(parts_dir):
        return parts_dir
    else:
        return None


class PublishFTPMaster(LaunchpadCronScript):
    """Publish a distro (update)."""

    def add_my_options(self):
        self.parser.add_option(
            '-d', '--distribution', dest='distribution', default=None,
            help="Distribution to publish.")
        self.parser.add_option(
            '-s', '--security-only', dest='security_only',
            action='store_true', default=False, help="Security upload only.")

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

    def executeShell(self, command_line, failure=None):
        """Run `command_line` through a shell.

        This won't just load an external program and run it; the command
        line goes through the full shell treatment including variable
        substitutions, output redirections, and so on.

        :param command_line: Shell command.
        :param failure: Raise `failure` as an exception if the shell
            command returns a nonzero value.  If omitted, nonzero return
            values are ignored.
        """
        self.logger.debug("Executing: %s" % command_line)
        retval = os.system(command_line)
        if retval != 0:
            self.logger.debug("Command returned %d.", retval)
            if failure is not None:
                self.logger.debug("Command failed: %s", failure)
                raise failure

    def getArchives(self):
        """Find archives for `self.distribution` that should be published."""
        # XXX JeroenVermeulen 2011-03-31 bug=746229: to start publishing
        # debug archives, change this to return
        # list(self.distribution.all_distro_archives).
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

    def rollBackArchiveNewDists(self, archive_purpose):
        """Move dists.new directory back into distscopy."""
        archive_config = self.configs[archive_purpose]
        self.logger.debug(
            "Moving %s dists backup to safe keeping for next time.",
            archive_purpose.title)
        dists_new = get_dists(archive_config, ".new")
        if file_exists(dists_new):
            dists = get_backup_dists(archive_config)
            self.logger.debug("Renaming %s to %s.", dists_new, dists)
            os.rename(dists_new, dists)

    def rollBackNewDists(self):
        """Restore distscopy versions of dists directories."""
        self.logger.debug("Cleaning up.")
        for purpose in self.configs.iterkeys():
            self.rollBackArchiveNewDists(purpose)

    def processAccepted(self):
        """Run the process-accepted script."""
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
        return receiver.argument.split()

    def getDirtySecuritySuites(self):
        """List security suites with pending publications."""
        suites = self.getDirtySuites()
        return [suite for suite in suites if suite.endswith('-security')]

    def rsyncNewDists(self, archive_purpose):
        """Populate dists.new with a copy of distsroot.

        Uses "rsync -aH --delete" so that any obsolete files that may
        still be in dists.new are cleaned up (bug 58835).

        :param archive_purpose: The (purpose of the) archive to copy.
        """
        archive_config = self.configs[archive_purpose]
        self.executeShell(
            "rsync -aH --delete '%s/' '%s'"
            % (get_dists(archive_config), get_backup_dists(archive_config)),
            failure=LaunchpadScriptFailure(
                "Failed to rsync new dists for %s." % archive_purpose.title))

    def updateNewDists(self):
        """Set up the new dists directories based on the current ones.

        Renames the backup dists directories to dists.new, then updates
        them from the current ones using rsync.
        """
        for purpose in self.configs.iterkeys():
            self.rsyncNewDists(purpose)
        for purpose in self.configs.iterkeys():
            self.renameBackupDistsToNewDists(purpose)

    def createMissingDirs(self, archive_purpose):
        """Create archive root and such if they did not yet exist."""
        archive_config = self.configs[archive_purpose]
        archiveroot = archive_config.archiveroot
        if not file_exists(archiveroot):
            self.logger.debug("Creating archive root %s.", archiveroot)
            os.makedirs(archiveroot)
        dists = get_dists(archive_config)
        if not file_exists(dists):
            self.logger.debug("Creating dists root %s.", dists)
            os.makedirs(dists)
        distscopy = get_backup_dists(archive_config)
        if not file_exists(distscopy):
            self.logger.debug(
                "Creating backup dists directory %s for %s",
                distscopy, archive_purpose.title)
            os.makedirs(distscopy)

    def renameBackupDistsToNewDists(self, archive_purpose):
        """Rename distscopy dists to dists.new."""
        archive_config = self.configs[archive_purpose]
        dists_new = get_dists(archive_config, ".new")
        self.logger.debug(
            "Moving backup dist for %s into place.", archive_purpose.title)
        os.rename(get_backup_dists(archive_config), dists_new)

    def setUpDirs(self):
        """Move dists directories to dists.new, or create them.

        We do this so that we don't get an inconsistent dists tree at
        any point during the publishing cycle (which would cause buildds
        to explode).

        This is done through maintaining a persistent backup copy of the
        dists directory, which we move into place and bring up to
        date with rsync.  Should achieve the same effect as copying, but
        faster.

        The counterpart of this method is `restoreDistsCopy`.  Once both
        have been called, the dists directories will be in place.  If
        the script fails before it can get to that point, call
        `rollBackNewDists` instead.
        """
        # Set up various directories if they do not yet exist.
        for purpose in self.configs.iterkeys():
            self.createMissingDirs(purpose)

    def publishDistroArchive(self, archive, security_suites=None):
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
            '-R', get_dists(archive_config, '.new'),
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
            'ARCHIVEROOT': archive_config.archiveroot,
            'DISTSROOT': get_dists(archive_config, ".new"),
            'OVERRIDEROOT': archive_config.overrideroot,
            }
        self.runParts('publish-distro.d', env)

    def installDists(self):
        """Put the new dists into place, as near-atomically as possible."""
        # Before we start moving directories around, make as nearly
        # sure as possible that we can do either none or all of them.
        self.logger.debug("Looking for impediments to publication.")
        for purpose, archive_config in self.configs.iteritems():
            old_dists = get_dists(archive_config, '.old')
            if file_exists(old_dists):
                raise LaunchpadScriptFailure(
                    "Old %s distsroot %s is in the way."
                    % (purpose.title, old_dists))

        # Move the existing distsroots out of the way, and move the new
        # ones in their place.
        self.logger.debug("Placing the new dists into place...")
        for archive_config in self.configs.itervalues():
            dists = get_dists(archive_config)
            os.rename(dists, get_dists(archive_config, ".old"))
            os.rename(get_dists(archive_config, ".new"), dists)

    def restoreDistsCopy(self):
        """Move dists.old back to the distscopy backup."""
        for purpose, archive_config in self.configs.iteritems():
            dists_old = get_dists(archive_config, ".old")
            dists_backup = get_backup_dists(archive_config)
            os.rename(dists_old, dists_backup)

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
        if not config.archivepublisher.run_commercial_compat:
            return

        self.executeShell("""
            env PATH="$PATH:%s/cronscripts/publishing" \
                LPCONFIG="%s" \
                commercial-compat.sh
            """ % (config.root, config.instance_name))

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
            self.executeShell(
                "cd -- '%s' ; TZ=UTC ls -lR | gzip -9n >'%s'"
                % (archive_config.archiveroot, lslr_new),
                failure=LaunchpadScriptFailure(
                    "Failed to create %s for %s." % (lslr, purpose.title)))
            os.rename(new_lslr_file, lslr_file)

    def clearEmptyDirs(self):
        """Clear out any redundant empty directories."""
        for archive_config in self.configs.itervalues():
            self.executeShell(
                "find '%s' -type d -empty | xargs -r rmdir"
                % archive_config.archiveroot)

    def runParts(self, parts, env):
        """Execute run-parts.

        :param parts: The run-parts directory to execute:
            "publish-distro.d" or "finalize.d".
        :param env: A dict of environment variables to pass to the
            scripts in the run-parts directory.
        """
        parts_dir = find_run_parts_dir(self.distribution, parts)
        if parts_dir is None:
            self.logger.debug("Skipping run-parts %s: not configured.", parts)
            return
        total_env_string = ' '.join([
            "PATH=\"$PATH:%s/cronscripts/publishing\"" % config.root,
            compose_env_string(env),
            ])
        self.executeShell(
            "env %s run-parts -- '%s'" % (total_env_string, parts_dir),
            failure=LaunchpadScriptFailure(
                "Failure while executing run-parts %s." % parts_dir))

    def runFinalizeParts(self, security_only=False):
        """Run the finalize.d parts to finalize publication."""
        env = {
            'SECURITY_UPLOAD_ONLY': compose_shell_boolean(security_only),
            'ARCHIVEROOTS': ' '.join([
                archive_config.archiveroot
                for archive_config in self.configs.itervalues()]),
        }
        self.runParts('finalize.d', env)

    def publishSecurityUploads(self):
        """Quickly process just the pending security uploads."""
        self.logger.debug("Expediting security uploads.")
        security_suites = self.getDirtySecuritySuites()
        if len(security_suites) == 0:
            self.logger.debug("Nothing to do for security publisher.")
            return

        self.publishDistroArchive(
            self.distribution.main_archive, security_suites=security_suites)

    def publishAllUploads(self):
        """Publish the distro's complete uploads."""
        self.logger.debug("Full publication.  This may take some time.")
        for archive in self.archives:
            # This, for the main archive, is where the script spends
            # most of its time.
            self.publishDistroArchive(archive)

    def publish(self, security_only=False):
        """Do the main publishing work.

        :param security_only: If True, limit publication to security
            updates on the main archive.  This is much faster, so it
            makes sense to do a security-only run before the main
            event to expedite critical fixes.
        """
        try:
            self.updateNewDists()

            if security_only:
                self.publishSecurityUploads()
            else:
                self.publishAllUploads()

            self.installDists()
        except:
            self.rollBackNewDists()
            raise

        # Bring us back to a state where we have a dists and a dists
        # copy (but switched around from how they started out).
        self.restoreDistsCopy()

    def setUp(self):
        """Process options, and set up internal state."""
        self.processOptions()
        self.archives = self.getArchives()
        self.configs = self.makeConfigs()

    def main(self):
        """See `LaunchpadScript`."""
        self.setUp()
        self.processAccepted()
        self.setUpDirs()

        self.publish(security_only=True)

        self.runCommercialCompat()
        self.runFinalizeParts(security_only=True)

        if not self.options.security_only:
            self.publish(security_only=False)

            self.runCommercialCompat()
            self.generateListings()
            self.clearEmptyDirs()
            self.runFinalizeParts()
