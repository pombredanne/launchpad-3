# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Processor interfaces."""

__metaclass__ = type

__all__ = [
    'IProcessor',
    'IProcessorFamily',
    'IProcessorFamilySet',
    ]

from zope.interface import Interface, Attribute

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

class IProcessorFamilySet(Interface):
    """Operations related to ProcessorFamily instances."""
    def getByName(name):
        """Return the ProcessorFamily instance with the matching name.

        :param name: The name to look for.

        :return: A `IProcessorFamily` instance if found, None otherwise.
        """

    def getByProcessorName(name):
        """Given a processor name return the ProcessorFamily it belongs to.

        :param name: The name of the processor to look for.

        :return: A `IProcessorFamily` instance if found, None otherwise.
        """
