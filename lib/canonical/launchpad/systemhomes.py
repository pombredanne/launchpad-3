# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""This module contains the content classes for the 'home pages' of the
subsystems of Launchpad.
"""
__metaclass__ = type

from zope.interface import implements
from canonical.launchpad.interfaces import (
    IDOAPApplication, IFOAFApplication, IMaloneApplication, IBazaarApplication
    )


class DOAPApplication:
    implements(IDOAPApplication)


class FOAFApplication:
    implements(IFOAFApplication)


class MaloneApplication:
    implements(IMaloneApplication)

    def __init__(self):
        self.title = 'Malone: Bug Management in Launchpad'


class BazaarApplication:
    implements(IBazaarApplication)

    def __init__(self):
        self.title = 'The Open Source Bazaar'

