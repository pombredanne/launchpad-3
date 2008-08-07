# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to IDiff."""

__metaclass__ = type

__all__ = [
    'IDiff',
    'IStaticDiffReference'
    ]

from zope.schema import (
    Object, Choice, Int, Text, TextLine)
from zope.interface import (
    Interface, Attribute)

class IDiff(Interface):
    pass

class IStaticDiffReference(Interface):
    pass
