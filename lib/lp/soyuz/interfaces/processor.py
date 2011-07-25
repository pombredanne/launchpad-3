# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Processor interfaces."""

__metaclass__ = type

__all__ = [
    'IProcessor',
    'IProcessorFamily',
    'IProcessorFamilySet',
    'IProcessorSet',
    'ProcessorNotFound',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Text,
    TextLine,
    )

from canonical.launchpad import _
from lazr.restful.declarations import (
    collection_default_content,
    export_as_webservice_collection,
    export_as_webservice_entry,
    export_read_operation,
    exported,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from lp.app.errors import NameLookupFailed


class ProcessorNotFound(NameLookupFailed):
    """Exception raised when a processor name isn't found."""
    _message_prefix = 'No such processor'


class IProcessor(Interface):
    """The SQLObject Processor Interface"""

    # XXX: BradCrittenden 2011-06-20 bug=760849: The following use of 'beta'
    # is a work-around to allow the WADL to be generated.  It is a bald-faced
    # lie, though.  The class is being exported in 'devel' but in order to get
    # the WADL generation work it must be back-dated to the earliest version.
    # Note that individual attributes and methods can and must truthfully set
    # 'devel' as their version.
    export_as_webservice_entry(publish_web_link=False, as_of='beta')
    id = Attribute("The Processor ID")
    family = exported(
        Reference(
            schema=Interface,
            # Really IProcessorFamily.
            required=True, readonly=True,
            title=_("Processor Family"),
            description=_("The Processor Family Reference")),
        as_of='devel', readonly=True)
    name = exported(
        TextLine(title=_("Name"),
                 description=_("The Processor Name")),
        as_of='devel', readonly=True)
    title = exported(
        TextLine(title=_("Title"),
                 description=_("The Processor Title")),
        as_of='devel', readonly=True)
    description = exported(
        Text(title=_("Description"),
             description=_("The Processor Description")),
        as_of='devel', readonly=True)


class IProcessorFamily(Interface):
    """The SQLObject ProcessorFamily Interface"""

    # XXX: BradCrittenden 2011-06-20 bug=760849: The following use of 'beta'
    # is a work-around to allow the WADL to be generated.  It is a bald-faced
    # lie, though.  The class is being exported in 'devel' but in order to get
    # the WADL generation work it must be back-dated to the earliest version.
    # Note that individual attributes and methods can and must truthfully set
    # 'devel' as their version.
    export_as_webservice_entry(
        plural_name='processor_families',
        publish_web_link=False,
        as_of='beta')

    id = Attribute("The ProcessorFamily ID")
    name = exported(
        TextLine(
            title=_("Name"),
            description=_("The Processor Family Name")),
        as_of='devel', readonly=True)
    title = exported(
        TextLine(
            title=_("Title"),
            description=_("The Processor Family Title")),
        as_of='devel', readonly=True)
    description = exported(
        Text(
            title=_("Description"),
            description=_("The Processor Name Description")),
        as_of='devel', readonly=True)
    processors = exported(
        CollectionField(
            title=_("Processors"),
            description=_("The Processors in this family."),
            value_type=Reference(IProcessor)),
        as_of='devel', readonly=True)
    restricted = exported(
        Bool(title=_("Whether this family is restricted.")),
        as_of='devel', readonly=True)

    def addProcessor(name, title, description):
        """Add a new processor to this family.

        :param name: Name of the processor
        :param title: Title of the processor
        :param description: Description of the processor
        :return: A `IProcessor`
        """


class IProcessorSet(Interface):
    """Operations related to Processor instances."""
    export_as_webservice_collection(IProcessor)

    @operation_parameters(
        name=TextLine(required=True))
    @operation_returns_entry(IProcessor)
    @export_read_operation()
    @operation_for_version('devel')
    def getByName(name):
        """Return the IProcessor instance with the matching name.

        :param name: The name to look for.
        :raise ProcessorNotFound: if there is no processor with that name.
        :return: A `IProcessor` instance if found
        """

    @collection_default_content()
    def getAll():
        """Return all the `IProcessor` known to Launchpad."""


class IProcessorFamilySet(Interface):
    """Operations related to ProcessorFamily instances."""

    export_as_webservice_collection(IProcessorFamily)

    @operation_parameters(
        name=TextLine(required=True))
    @operation_returns_entry(IProcessorFamily)
    @export_read_operation()
    @operation_for_version('devel')
    def getByName(name):
        """Return the ProcessorFamily instance with the matching name.

        :param name: The name to look for.

        :return: A `IProcessorFamily` instance if found, None otherwise.
        """

    @collection_default_content()
    def getRestricted():
        """Return a sequence of all restricted architectures.

        :return: A sequence of `IProcessorFamily` instances.
        """

    def getByProcessorName(name):
        """Given a processor name return the ProcessorFamily it belongs to.

        :param name: The name of the processor to look for.

        :return: A `IProcessorFamily` instance if found, None otherwise.
        """

    def new(name, title, description, restricted):
        """Create a new processor family.

        :param name: Name of the family.
        :param title: Title for the family.
        :param description: Extended description of the family
        :param restricted: Whether the processor family is restricted
        :return: a `IProcessorFamily`.
        """
