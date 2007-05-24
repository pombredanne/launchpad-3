# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Builder interfaces."""

__metaclass__ = type

__all__ = [
    'BuildDaemonError',
    'BuildJobMismatch',
    'IBuilder',
    'IBuilderSet',
    'ProtocolVersionMismatch',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, TextLine, Text, Bool

from canonical.launchpad import _
from canonical.launchpad.fields import Title, Description
from canonical.launchpad.interfaces.launchpad import IHasOwner
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.validators.url import builder_url_validator


class BuildDaemonError(Exception):
    """The class of errors raised by the buildd classes"""


class ProtocolVersionMismatch(BuildDaemonError):
    """The build slave had a protocol version. This is a serious error."""


class BuildJobMismatch(BuildDaemonError):
    """The build slave is working with mismatched information, needs rescue."""


class IBuilder(IHasOwner):
    """Build-slave information and state.

    Builder instance represents a single builder slave machine within the
    Launchpad Auto Build System. It should specify a 'processor' on which the
    machine is based and is able to build packages for; a URL, by which the
    machine is accessed through an XML-RPC interface; name, title,
    description for entity identification and browsing purposes; an LP-like
    owner which has unrestricted access to the instance; the build slave
    machine status representation, including the field/properties: trusted,
    builderok, status, failnotes and currentjob.
    """
    id = Attribute("Builder identifier")
    processor = Choice(title=_('Processor'), required=True,
                       vocabulary='Processor',
                       description=_('Build Slave Processor, used to identify '
                                     'which jobs can be built by this device.')
                       )

    owner = Choice(title=_('Owner'), required=True,
                   vocabulary='ValidOwner',
                   description=_('Builder owner, a Launchpad member which '
                                 'will be responsible for this device.')
                   )

    url = TextLine(title=_('URL'), required=True,
                   constraint=builder_url_validator,
                   description=_('The URL to the build machine, used as a '
                                 'unique identifier. Includes protocol, '
                                 'host and port only, '
                                 'e.g.: http://farm.com:8221/')
                   )
    name = TextLine(title=_('Name'), required=True,
                    constraint=name_validator,
                    description=_('Builder Slave Name used for reference '
                                  'proposes')
                    )
    title = Title(title=_('Title'), required=True,
                  description=_('The builder slave title. Should be just '
                                'a few words.')
                  )

    description = Description(title=_('Description'), required=True,
                              description=_('The builder slave description, '
                                            'may be several paragraphs of '
                                            'text, giving the highlights '
                                            'and details.')
                              )

    trusted = Bool(title=_('Trusted'), required=True,
                   description=_('Whether or not the builder is prepared '
                                 'to build untrusted packages.')
                   )

    manual = Bool(title=_('Manual Mode'), required=False,
                   description=_('The auto-build system does not dispatch '
                                 'jobs automatically for slaves in manual '
                                 'mode.')
                   )

    builderok = Bool(title=_('Builder State OK'), required=False,
                     description=_('Whether or not the builder is ok')
                     )

    failnotes = Text(title=_('Failure Notes'), required=False,
                     description=_('The reason for a builder not being ok')
                     )

    slave = Attribute("xmlrpclib.Server instance corresponding to builder.")
    currentjob = Attribute("Build Job being processed")
    status = Attribute("Generated status information")

    def cacheFileOnSlave(logger, libraryfilealias):
        """Ask the slave to cache a librarian file to its local disk.

        This is used in preparation for a build.

        :param logger: A logger used for providing debug information.
        :param libraryfilealias: A library file alias representing the needed
            file.
        """

    def checkCanBuildForDistroArchRelease(distro_arch_release):
        """Check that the slave is able to compile for the supplied distro_arch_release.

        This will query the builder to determine its actual architecture (as
        opposed to what we expect it to be).

        :param distro_arch_release: The distro_arch_release to check against.
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

    def cleanSlave():
        """Clean any temporary files from the slave."""

    def failbuilder(reason):
        """Mark builder as failed for a given reason."""

    def slaveStatusSentence():
        """Get the slave status sentence for this builder.

        :return: A tuple with the first element containing the slave status,
            build_id-queue-id and then optionally more elements depending on
            the status.
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
            trusted=False):
        """Create a new Builder entry."""

    def count():
        """Return the number of builders in the system."""

    def get(builder_id):
        """Return the IBuilder with the given builderid."""

    def getBuilders():
        """Return all configured builders."""

    def getBuildersByArch(arch):
        """Return all configured builders for a given DistroArchRelease."""

    def pollBuilders(logger, txn):
        """Poll all the builders and take any immediately available actions.

        Specifically this will request a reset if needed, update log tails in
        the database, copy and process the result of builds.

        :param logger: A logger to use to provide information about the polling
            process.
        :param txn: A zopeless transaction object which is currently used by
            legacy code that we are in the process of removing. DO NOT add
            additional uses of this parameter.
        :return: A canonical.buildmaster.master.BuilddMaster instance. This is
            temporary and once the dispatchBuilds method no longer requires
            a used instance this return parameter will be dropped.
        """

    def dispatchBuilds(logger, buildMaster):
        """Dispatch any pending builds that can be dispatched.

        :param logger: A logger to use to provide information about the
            dispatching process.
        :param buildMaster: This is a canonical.buildmaster.master.BuilddMaster
            instance which will be used to perform the dispatching as that is
            where the detailed logic currently resides. This is being
            refactored to remove the need for a buildMaster parameter at all.
        """
