# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""This module contains the content classes for the 'home pages' of the
subsystems of launchpad.
"""
__metaclass__ = type

from zope.interface import implements
from canonical.launchpad.interfaces import IDOAPApplication, IFOAFApplication


class DOAPApplication:
    implements(IDOAPApplication)


class FOAFApplication:
    implements(IFOAFApplication)
