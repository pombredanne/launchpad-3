# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Builder interfaces."""

__metaclass__ = type

__all__ = [
    'BuildDaemonError',
    'CorruptBuildCookie',
    'BuildSlaveFailure',
    'CannotBuild',
    'CannotFetchFile',
    'CannotResumeHost',
    'IBuilder',
    'IBuilderSet',
    'ProtocolVersionMismatch',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Field, Int, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import Title, Description
from lp.registry.interfaces.role import IHasOwner
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.validators.url import builder_url_validator


class BuildDaemonError(Exception):
    """The class of errors raised by the buildd classes"""


class CannotFetchFile(BuildDaemonError):
    """The slave was unable to fetch the file."""

    def __init__(self, file_url, error_information):
        super(CannotFetchFile, self).__init__()
        self.file_url = file_url
        self.error_information = error_information


class ProtocolVersionMismatch(BuildDaemonError):
    """The build slave had a protocol version. This is a serious error."""


class CorruptBuildCookie(BuildDaemonError):
    """The build slave is working with mismatched information.

    It needs to be rescued.
    """


class CannotResumeHost(BuildDaemonError):
    """The build slave virtual machine cannot be resumed."""


# CannotBuild is intended to be the base class for a family of more specific
# errors.
class CannotBuild(BuildDaemonError):
    """The requested build cannot be done."""


class BuildSlaveFailure(BuildDaemonError):
    """The build slave has suffered an error and cannot be used."""


class IBuilder(IHasOwner):
    """Build-slave information and state.

    Builder instance represents a single builder slave machine within the
    Launchpad Auto Build System. It should specify a 'processor' on which the
    machine is based and is able to build packages for; a URL, by which the
    machine is accessed through an XML-RPC interface; name, title,
    description for entity identification and browsing purposes; an LP-like
    owner which has unrestricted access to the instance; the build slave
    machine status representation, including the field/properties:
    virtualized, builderok, status, failnotes and currentjob.
    """
    id = Attribute("Builder identifier")
    processor = Choice(
        title=_('Processor'), required=True, vocabulary='Processor',
        description=_('Build Slave Processor, used to identify '
                      'which jobs can be built by this device.'))

    owner = Choice(
        title=_('Owner'), required=True, vocabulary='ValidOwner',
        description=_('Builder owner, a Launchpad member which '
                      'will be responsible for this device.'))

    url = TextLine(
        title=_('URL'), required=True, constraint=builder_url_validator,
        description=_('The URL to the build machine, used as a unique '
                      'identifier. Includes protocol, host and port only, '
                      'e.g.: http://farm.com:8221/'))

    name = TextLine(
        title=_('Name'), required=True, constraint=name_validator,
        description=_('Builder Slave Name used for reference proposes'))

    title = Title(
        title=_('Title'), required=True,
        description=_('The builder slave title. Should be just a few words.'))

    description = Description(
        title=_('Description'), required=False,
        description=_('The builder slave description, may be several '
                      'paragraphs of text, giving the highlights and '
                      'details.'))

    virtualized = Bool(
        title=_('Virtualized'), required=True, default=False,
        description=_('Whether or not the builder is a virtual Xen '
                      'instance.'))

    manual = Bool(
        title=_('Manual Mode'), required=False, default=False,
        description=_('The auto-build system does not dispatch '
                      'jobs automatically for slaves in manual mode.'))

    builderok = Bool(
        title=_('Builder State OK'), required=True, default=True,
        description=_('Whether or not the builder is ok'))

    failnotes = Text(
        title=_('Failure Notes'), required=False,
        description=_('The reason for a builder not being ok'))

    vm_host = TextLine(
        title=_('Virtual Machine Host'), required=False,
        description=_('The machine hostname hosting the virtual '
                      'buildd-slave, e.g.: foobar-host.ppa'))

    active = Bool(
        title=_('Active'), required=True, default=True,
        description=_('Whether or not to present the builder publicly.'))

    slave = Attribute("xmlrpclib.Server instance corresponding to builder.")

    currentjob = Attribute("BuildQueue instance for job being processed.")

    is_available = Bool(
        title=_("Whether or not a builder is available for building "
                "new jobs. "),
        required=False)

    failure_count = Int(
        title=_('Failure Count'), required=False, default=0,
        description=_("Number of consecutive failures for this builder."))

    current_build_behavior = Field(
        title=u"The current behavior of the builder for the current job.",
        required=False)

    def checkSlaveArchitecture():
        """Check that the slave can compile for its nominated processor.

        This will query the builder to determine its actual architecture (as
        opposed to what we expect it to be). It will then look for a
        DistroArchSeries with the returned architecture tag, and confirm that
        the processor type matches.

        :raises BuildDaemonError: When the builder is down or of the wrong
            architecture.
        :raises ProtocolVersionMismatch: When the builder returns an
            unsupported protocol version.
        """

    def checkSlaveAlive():
        """Check that the buildd slave is alive.

        This pings the slave over the network via the echo method and looks
        for the sent message as the reply.

        :raises BuildDaemonError: When the slave is down.
        """

    def rescueIfLost(logger=None):
        """Reset the slave if its job information doesn't match the DB.

        If the builder is BUILDING or WAITING but has a build ID string
        that doesn't match what is stored in the DB, we have to dismiss
        its current actions and clean the slave for another job, assuming
        the XMLRPC is working properly at this point.
        """

    def updateStatus(logger=None):
        """Update the builder's status by probing it."""

    def cleanSlave():
        """Clean any temporary files from the slave."""

    def failBuilder(reason):
        """Mark builder as failed for a given reason."""

    def requestAbort():
        """Ask that a build be aborted.

        This takes place asynchronously: Actually killing everything running
        can take some time so the slave status should be queried again to
        detect when the abort has taken effect. (Look for status ABORTED).
        """

    def resumeSlaveHost():
        """Resume the slave host to a known good condition.

        Issues 'builddmaster.vm_resume_command' specified in the configuration
        to resume the slave.

        :raises: CannotResumeHost: if builder is not virtual or if the
            configuration command has failed.

        :return: command stdout and stderr buffers as a tuple.
        """

    def setSlaveForTesting(proxy):
        """Sets the RPC proxy through which to operate the build slave."""

    def slaveStatus():
        """Get the slave status for this builder.

        :return: a dict containing at least builder_status, but potentially
            other values included by the current build behavior.
        """

    def slaveStatusSentence():
        """Get the slave status sentence for this builder.

        :return: A tuple with the first element containing the slave status,
            build_id-queue-id and then optionally more elements depending on
            the status.
        """

    def verifySlaveBuildCookie(slave_build_id):
        """Verify that a slave's build cookie is consistent.

        This should delegate to the current `IBuildFarmJobBehavior`.
        """

    def updateBuild(queueItem):
        """Verify the current build job status.

        Perform the required actions for each state.
        """

    def startBuild(build_queue_item, logger):
        """Start a build on this builder.

        :param build_queue_item: A BuildQueueItem to build.
        :param logger: A logger to be used to log diagnostic information.
        :raises BuildSlaveFailure: When the build slave fails.
        :raises CannotBuild: When a build cannot be started for some reason
            other than the build slave failing.
        """

    def transferSlaveFileToLibrarian(file_sha1, filename, private):
        """Transfer a file from the slave to the librarian.

        :param file_sha1: The file's sha1, which is how the file is addressed
            in the slave XMLRPC protocol. Specially, the file_sha1 'buildlog'
            will cause the build log to be retrieved and gzipped.
        :param filename: The name of the file to be given to the librarian file
            alias.
        :param private: True if the build is for a private archive.
        :return: A librarian file alias.
        """

    def handleTimeout(logger, error_message):
        """Handle buildd slave communication timeout situations.

        In case of a virtualized/PPA buildd slave an attempt will be made
        to reset it first (using `resumeSlaveHost`). Only if that fails
        will it be (marked as) failed (using `failBuilder`).

        Conversely, a non-virtualized buildd slave will be (marked as)
        failed straightaway.

        :param logger: The logger object to be used for logging.
        :param error_message: The error message to be used for logging.
        """

    def findAndStartJob(buildd_slave=None):
        """Find a job to run and send it to the buildd slave.

        :param buildd_slave: An optional buildd slave that this builder should
            talk to.
        :return: the `IBuildQueue` instance found or None if no job was found.
        """


class IBuilderSet(Interface):
    """Collections of builders.

    IBuilderSet provides access to all Builders in the system,
    and also acts as a Factory to allow the creation of new Builders.
    Methods on this interface should deal with the set of Builders:
    methods that affect a single Builder should be on IBuilder.
    """

    title = Attribute('Title')

    def __iter__():
        """Iterate over builders."""

    def __getitem__(name):
        """Retrieve a builder by name"""

    def new(processor, url, name, title, description, owner,
            active=True, virtualized=False, vm_host=None):
        """Create a new Builder entry.

        Additionally to the given arguments, builder are created with
        'builderok' and 'manual' set to True.

        It means that, once created, they will be presented as 'functional'
        in the UI but will not receive any job until an administrator move
        it to the automatic mode.
        """

    def count():
        """Return the number of builders in the system."""

    def get(builder_id):
        """Return the IBuilder with the given builderid."""

    def getBuilders():
        """Return all active configured builders."""

    def getBuildersByArch(arch):
        """Return all configured builders for a given DistroArchSeries."""

    def getBuildQueueSizes():
        """Return the number of pending builds for each processor.

        :return: a dict of tuples with the queue size and duration for
            each processor and virtualisation. For example:
            {
                'virt': {
                            '386': (1, datetime.timedelta(0, 60)),
                            'amd64': (2, datetime.timedelta(0, 30)),
                        },
                'nonvirt':...
            }

            The tuple contains the size of the queue, as an integer,
            and the sum of the jobs 'estimated_duration' in queue,
            as a timedelta or None for empty queues.
        """

    def pollBuilders(logger, txn):
        """Poll all the builders and take any immediately available actions.

        Specifically this will request a resume if needed, update log tails in
        the database, copy and process the result of builds.

        :param logger: A logger to use to provide information about the polling
            process.
        :param txn: A zopeless transaction object which is currently used by
            legacy code that we are in the process of removing. DO NOT add
            additional uses of this parameter.
        """

    def checkBuilders(logger, txn):
        """Update the status of all builders and commit."""

    def scanActiveBuilders(logger, txn):
        """Scan all active builders, updating the current build jobs."""

    def getBuildersForQueue(processor, virtualized):
        """Return all builders for given processor/virtualization setting."""
