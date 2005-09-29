# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Processor interfaces."""

__metaclass__ = type

__all__ = [
    'IProcessor',
    'IProcessorFamily',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IProcessor(Interface):
    """The SQLObject Processor Interface"""
    id = Attribute("The Processor ID")
    family = Attribute("The Processor Family Reference")
    name = Attribute("The Processor Name")
    title = Attribute("The Processor Title")
    description = Attribute("The Processor Description")

class IProcessorFamily(Interface):
    """The SQLObject ProcessorFamily Interface"""
    name = Attribute("The Processor Family Name")
    title = Attribute("The Processor Family Title")
    description = Attribute("The Processor Name Description")

