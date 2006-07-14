# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Build interfaces."""

__metaclass__ = type

__all__ = [
    'IBuilder',
    'IBuilderSet',
    'IBuildQueue',
    'IBuildQueueSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, TextLine, Text, Bool

from canonical.launchpad import _
from canonical.launchpad.fields import Title, Description
from canonical.launchpad.interfaces.launchpad import IHasOwner
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.validators.url import builder_url_validator

    
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
                   description=_('Whether or not the builder is trusted to '
                                 'build packages under security embargo.')
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

    def failbuilder(reason):
        """Mark builder as failed for a given reason."""


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


class IBuildQueue(Interface):
    """A launchpad Auto Build queue entry"""

    id = Attribute("Job identifier")
    build = Attribute("The build in question")
    builder = Attribute("The builder building the build")
    created = Attribute("The datetime that the queue entry waw created")
    buildstart = Attribute("The datetime of the last build attempt")
    logtail = Attribute("The current tail of the log of the build")
    lastscore = Attribute("Last score to be computed for this job")
    archrelease = Attribute("the build DistroArchRelease")
    urgency = Attribute("SourcePackageRelease Urgency")
    component_name = Attribute("Component name where the job got published")
    archhintlist = Attribute("SourcePackageRelease archhintlist")
    name = Attribute("SourcePackageRelease name")
    version = Attribute("SourcePackageRelease version")
    files = Attribute("SourcePackageRelease files")
    builddependsindep = Attribute("SourcePackageRelease builddependsindep")
    buildduration = Attribute("The duration of the build in progress")
    manual = Attribute("whether or not the record was rescored manually")

    def manualScore(value):
        """Manually set a score value to a queue item and lock it."""

    def destroySelf():
        """Delete this entry from the database."""


class IBuildQueueSet(Interface):
    """Launchpad Auto Build queue set handler and axiliary methods"""
    title = Attribute('Title')

    def __iter__():
        """Iterate over current build jobs."""

    def __getitem__(job_id):
        """Retrieve a build job by id"""

    def count():
        """Return the number of build jobs in the queue."""

    def get(job_id):
        """Return the IBuildQueue with the given jobid."""

    def getActiveBuildJobs():
        """Return All active Build Jobs."""

    def fetchByBuildIds(build_ids):
        """Used to pre-populate the cache with reversed referred keys.

        When dealing with a group of Build records we can't use pre-join
        facility to also fetch BuildQueue records in a single query,
        because Build and BuildQueue are related with reversed keys

        Build.id = BuildQueue.build

        So this method recieves a list of Build IDs and fetches the
        correspondent BuildQueue with prejoined builder information.

        It return the SelectResults or empty list if the passed builds
        is empty, but the result isn't might to be used in call site.
        """

    def calculateCandidates(archreleases, state):
        """Return the candidates for building

        The result is a unsorted list of buildqueue items in a given state
        within a given distroarchrelease group.
        """

