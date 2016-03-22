# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Builder interfaces."""

__metaclass__ = type

__all__ = [
    'BuildDaemonError',
    'BuildDaemonIsolationError',
    'BuildSlaveFailure',
    'CannotBuild',
    'CannotFetchFile',
    'CannotResumeHost',
    'IBuilder',
    'IBuilderSet',
    ]

from lazr.restful.declarations import (
    call_with,
    collection_default_content,
    export_as_webservice_collection,
    export_as_webservice_entry,
    export_factory_operation,
    export_read_operation,
    export_write_operation,
    exported,
    mutator_for,
    operation_for_version,
    operation_parameters,
    operation_returns_collection_of,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    Reference,
    ReferenceChoice,
    )
from lazr.restful.interface import copy_field
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    List,
    Text,
    TextLine,
    )

from lp import _
from lp.app.validators.name import name_validator
from lp.app.validators.url import builder_url_validator
from lp.buildmaster.enums import (
    BuilderCleanStatus,
    BuilderResetProtocol,
    )
from lp.buildmaster.interfaces.processor import IProcessor
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import (
    PersonChoice,
    Title,
    )
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords


class BuildDaemonError(Exception):
    """The class of errors raised by the buildd classes"""


class BuildDaemonIsolationError(BuildDaemonError):
    """A build isolation violation has been detected."""


class CannotFetchFile(BuildDaemonError):
    """The slave was unable to fetch the file."""

    def __init__(self, file_url, error_information):
        super(CannotFetchFile, self).__init__()
        self.file_url = file_url
        self.error_information = error_information


class CannotResumeHost(BuildDaemonError):
    """The build slave virtual machine cannot be resumed."""


# CannotBuild is intended to be the base class for a family of more specific
# errors.
class CannotBuild(BuildDaemonError):
    """The requested build cannot be done."""


class BuildSlaveFailure(BuildDaemonError):
    """The build slave has suffered an error and cannot be used."""


class IBuilderView(IHasBuildRecords, IHasOwner):

    id = Attribute("Builder identifier")

    processor = exported(ReferenceChoice(
        title=_('Processor'), required=True, vocabulary='Processor',
        schema=IProcessor,
        description=_(
            'DEPRECATED: Processor identifying jobs which can be built by '
            'this device. Use `processors` instead to handle multiple '
            'supported architectures.')),
        as_of='devel')

    processors = exported(
        List(
            title=_("Processors"),
            description=_(
                "Processors identifying jobs which can be built by this "
                "device."),
            value_type=ReferenceChoice(
                vocabulary='Processor', schema=IProcessor)),
        as_of='devel')

    owner = exported(PersonChoice(
        title=_('Owner'), required=True, vocabulary='ValidOwner',
        description=_('Builder owner, a Launchpad member which '
                      'will be responsible for this device.')))

    url = exported(TextLine(
        title=_('URL'), required=True, constraint=builder_url_validator,
        description=_('The URL to the build machine, used as a unique '
                      'identifier. Includes protocol, host and port only, '
                      'e.g.: http://farm.com:8221/')))

    name = exported(TextLine(
        title=_('Name'), required=True, constraint=name_validator,
        description=_('Builder Slave Name used for reference purposes')))

    title = exported(Title(
        title=_('Title'), required=True,
        description=_(
            'The builder slave title. Should be just a few words.')))

    virtualized = exported(Bool(
        title=_('Virtualized'), required=True, default=False,
        description=_('Whether or not the builder is a virtual Xen '
                      'instance.')))

    manual = exported(Bool(
        title=_('Manual Mode'), required=False, default=False,
        description=_('The auto-build system does not dispatch '
                      'jobs automatically for slaves in manual mode.')))

    builderok = exported(Bool(
        title=_('Builder State OK'), required=True, default=True,
        description=_('Whether or not the builder is ok')))

    failnotes = exported(Text(
        title=_('Failure Notes'), required=False,
        description=_('The reason for a builder not being ok')))

    vm_host = exported(TextLine(
        title=_('VM host'), required=False,
        description=_('The machine hostname hosting the virtual '
                      'buildd-slave, e.g.: foobar-host.ppa')))

    vm_reset_protocol = exported(Choice(
        title=_("VM reset protocol"), vocabulary=BuilderResetProtocol,
        readonly=False, required=False,
        description=_("The protocol version for resetting the VM.")))

    active = exported(Bool(
        title=_('Publicly Visible'), required=False, default=True,
        description=_('Whether or not to present the builder publicly.')))

    currentjob = Attribute("BuildQueue instance for job being processed.")

    current_build = exported(Reference(
        title=_("Current build"), required=False, readonly=True,
        schema=Interface,  # Really IBuildFarmJob.
        description=_("The job currently running on this builder.")),
        as_of="devel")

    failure_count = exported(Int(
        title=_('Failure Count'), required=False, default=0,
       description=_("Number of consecutive failures for this builder.")))

    version = exported(Text(
        title=_('Version'), required=False,
        description=_('The version of launchpad-buildd on the slave.')))

    clean_status = exported(Choice(
        title=_("Clean status"), vocabulary=BuilderCleanStatus, readonly=True,
        description=_(
            "The readiness of the slave to take a job. Only internal build "
            "infrastructure bots need to or should write to this.")))

    date_clean_status_changed = exported(Datetime(
        title=_("Date clean status changed"), readonly=True,
        description=_("The date the builder's clean status last changed.")))

    def gotFailure():
        """Increment failure_count on the builder."""

    def resetFailureCount():
        """Set the failure_count back to zero."""

    def failBuilder(reason):
        """Mark builder as failed for a given reason."""

    def acquireBuildCandidate():
        """Acquire a build candidate in an atomic fashion.

        When retrieiving a candidate we need to mark it as building
        immediately so that it is not dispatched by another builder in the
        build manager.

        We can consider this to be atomic because although the build manager
        is a Twisted app and gives the appearance of doing lots of things at
        once, it's still single-threaded so no more than one builder scan
        can be in this code at the same time.

        If there's ever more than one build manager running at once, then
        this code will need some sort of mutex.
        """


class IBuilderEdit(Interface):

    @mutator_for(IBuilderView['clean_status'])
    @operation_parameters(status=copy_field(IBuilderView['clean_status']))
    @export_write_operation()
    @operation_for_version('devel')
    def setCleanStatus(status):
        """Update the clean status."""


class IBuilder(IBuilderEdit, IBuilderView):
    """Build-slave information and state.

    Builder instance represents a single builder slave machine within the
    Launchpad Auto Build System. It should specify a 'processor' on which the
    machine is based and is able to build packages for; a URL, by which the
    machine is accessed through an XML-RPC interface; name, title for entity
    identification and browsing purposes; an LP-like owner which has
    unrestricted access to the instance; the build slave machine status
    representation, including the field/properties: virtualized, builderok,
    status, failnotes and currentjob.
    """
    export_as_webservice_entry()


class IBuilderSetAdmin(Interface):

    @call_with(owner=REQUEST_USER)
    @export_factory_operation(
        IBuilder,
        ['processors', 'url', 'name', 'title', 'active', 'virtualized',
         'vm_host'])
    @operation_for_version('devel')
    def new(processors, url, name, title, owner, active=True,
            virtualized=False, vm_host=None):
        """Create a new builder.

        The builder will be set to manual. An admin needs to verify its
        configuration and set it to automatic before jobs will be
        dispatched.
        """


class IBuilderSet(IBuilderSetAdmin):
    """Collections of builders.

    IBuilderSet provides access to all Builders in the system,
    and also acts as a Factory to allow the creation of new Builders.
    Methods on this interface should deal with the set of Builders:
    methods that affect a single Builder should be on IBuilder.
    """
    export_as_webservice_collection(IBuilder)
    title = Attribute('Title')

    def __iter__():
        """Iterate over builders."""

    def __getitem__(name):
        """Retrieve a builder by name"""

    @operation_parameters(
        name=TextLine(title=_("Builder name"), required=True))
    @operation_returns_entry(IBuilder)
    @export_read_operation()
    def getByName(name):
        """Retrieve a builder by name"""

    def count():
        """Return the number of builders in the system."""

    def get(builder_id):
        """Return the IBuilder with the given builderid."""

    @collection_default_content()
    def getBuilders():
        """Return all active configured builders."""

    @export_read_operation()
    @operation_for_version('devel')
    def getBuildQueueSizes():
        """Return the number of pending builds for each processor.

        :return: a dict of tuples with the queue size and duration for
            each processor and virtualisation. For example::

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

    @operation_parameters(
        processor=Reference(
            title=_("Processor"), required=True, schema=IProcessor),
        virtualized=Bool(
            title=_("Virtualized"), required=False, default=True))
    @operation_returns_collection_of(IBuilder)
    @export_read_operation()
    @operation_for_version('devel')
    def getBuildersForQueue(processor, virtualized):
        """Return all builders for given processor/virtualization setting."""
