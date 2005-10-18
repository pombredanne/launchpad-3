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
from zope.i18nmessageid import MessageIDFactory
from zope.schema import Choice, TextLine, Bool

_ = MessageIDFactory('launchpad')

from canonical.launchpad.fields import Title, Description
from canonical.launchpad.interfaces.launchpad import IHasOwner
from canonical.launchpad.validators.name import valid_name


class IBuilder(IHasOwner):
    """Build-slave information and state.
    
    Builder instance represents a single builder slave instance within the
    Launchad Auto Build System. It should specify a 'processor' which the
    machine is based and able to build packages for; an URL, by which the
    entity get accessed through an XML-RPC interface; name, title,
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
                   description=_('Builder URL is user as unique device '
                                 'identification, includes protocol, host '
                                 'and port, e.g.: http://farm.com:8221')
                   )
    name = TextLine(title=_('Name'), required=True,
                    constraint=valid_name,
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
                                            'text, giving the its highlights '
                                            'and details.')
                              )

    trusted = Bool(title=_('Trusted'), required=True,
                   description=_('Whether not the builder is trusted to '
                                 'build packages under security embargo.')
                   )

    manual = Bool(title=_('Manual Mode'), required=False,
                   description=_('Whether not the builder is MANUAL MODE. '
                                 'Auto Build System does not dispach jobs '
                                 'automatically for slaves in that state')
                   )

    builderok = Attribute("Whether or not the builder is ok")
    failnotes = Attribute("The reason for a builder not being ok")
    slave = Attribute("xmlrpclib.Server instance correspondent to builder.")
    currentjob = Attribute("Build Job being processed")
    status = Attribute("Generated status information")

    def lastBuilds(limit=10):
        """Last Build Jobs finished

        Returns the SQLResult ordered by descend datebuild, default 'limit'
        is 10.
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

    def new(self, processor, url, name, title, description, owner,
            trusted=False):
        """Create a new Builder entry."""

    def count():
        """Return the number of builders in the system."""

    def get(builder_id):
        """Return the IBuilder with the given builderid."""

    def getBuilders():
        """Return all configured builders."""

    def getBuild(id):
        """Return a specific build by ID."""


class IBuildQueue(Interface):
    """A launchpad Auto Build queue entry"""

    id = Attribute("Job identifier")
    build = Attribute("The build in question")
    builder = Attribute("The builder building the build")
    created = Attribute("The datetime that the queue entry waw created")
    buildstart = Attribute("The datetime of the last build attempt")
    logtail = Attribute("The current tail of the log of the build")
    archrelease = Attribute("the build DistroArchRelease")
    urgency = Attribute("SourcePackageRelease Urgency")
    component_name = Attribute("Component name where the job got published")
    archhintlist = Attribute("SourcePackageRelease archhintlist")
    name = Attribute("SourcePackageRelease name")
    version = Attribute("SourcePackageRelease version")
    files = Attribute("SourcePackageRelease files")
    buildduration = Attribute("The duration of the build in progress")

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
    
