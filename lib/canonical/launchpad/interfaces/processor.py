# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Processor interfaces."""

__metaclass__ = type

__all__ = [
    'IProcessor',
    'IProcessorFamily',
    ]

from zope.interface import Interface, Attribute
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
