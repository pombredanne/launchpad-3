# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Code import machine interfaces."""

__metaclass__ = type

__all__ = [
    'ICodeImportMachine',
    'ICodeImportMachineSet',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, TextLine, Bool

from canonical.launchpad import _


class ICodeImportMachine(Interface):
    """A machine that can perform imports."""

    id = Int(readonly=True, required=True)

    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)

    hostname = TextLine(
        title=_('Host name'), required=True,
        description=_('The hostname of the machine.'))

    online = Bool(
        title=_('Online'), required=True,
        description=_('Is the machine currently online?'))


class ICodeImportMachineSet(Interface):
    """The set of machines that can perform imports."""

    def getAll():
        """Return an iterable of all code machines."""

    def getByHostname(hostname):
        """Retrieve the code import machine for a hostname.

        Returns a `ICodeImportMachine` provider or ``None`` if no such machine
        is present.
        """
