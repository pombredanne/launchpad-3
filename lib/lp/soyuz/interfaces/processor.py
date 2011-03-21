# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Processor interfaces."""

__metaclass__ = type

__all__ = [
    'IProcessor',
    'IProcessorFamily',
    'IProcessorFamilySet',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import Bool

from canonical.launchpad import _


class IProcessor(Interface):
    """The SQLObject Processor Interface"""
    id = Attribute("The Processor ID")
    family = Attribute("The Processor Family Reference")
    name = Attribute("The Processor Name")
    title = Attribute("The Processor Title")
    description = Attribute("The Processor Description")

class IProcessorFamily(Interface):
    """The SQLObject ProcessorFamily Interface"""
    id = Attribute("The ProcessorFamily ID")
    name = Attribute("The Processor Family Name")
    title = Attribute("The Processor Family Title")
    description = Attribute("The Processor Name Description")
    processors = Attribute("The Processors in this family.")
    restricted = Bool(title=_("Whether this family is restricted."))

    def addProcessor(name, title, description):
        """Add a new processor to this family.

        :param name: Name of the processor
        :param title: Title of the processor
        :param description: Description of the processor
        :return: A `IProcessor`
        """

class IProcessorFamilySet(Interface):
    """Operations related to ProcessorFamily instances."""

    def getByName(name):
        """Return the ProcessorFamily instance with the matching name.

        :param name: The name to look for.

        :return: A `IProcessorFamily` instance if found, None otherwise.
        """

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
