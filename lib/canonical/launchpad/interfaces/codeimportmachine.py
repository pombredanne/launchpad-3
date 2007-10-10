# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Code import machine interfaces."""

__metaclass__ = type

__all__ = [
    'ICodeImportMachine',
    'ICodeImportMachineSet',
    'CodeImportMachineOfflineReason',
    'CodeImportMachineState',
    ]

from zope.interface import Interface
from zope.schema import Choice, Datetime, Int, TextLine

from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem


class CodeImportMachineState(DBEnumeratedType):
    """CodeImportMachine State

    The operational state of the code-import-controller daemon on a given
    machine.
    """

    OFFLINE = DBItem(10, """
        Offline

        The code-import-controller daemon is not running on this machine.
        """)

    ONLINE = DBItem(20, """
        Online

        The code-import-controller daemon is running on this machine and
        accepting new jobs.
        """)

    QUIESCING = DBItem(30, """
        Quiescing

        The code-import-controller daemon is running on this machine, but has
        been requested to shut down and will not accept any new job.
        """)


class CodeImportMachineOfflineReason(DBEnumeratedType):
    """Reason why a CodeImportMachine is offline.

    A machine goes offline when a code-import-controller daemon process
    shutdowns or appears to have crashed. Recording the reason a machine went
    offline provides useful diagnostic information.
    """

    # Daemon termination

    STOPPED = DBItem(110, """
        Stopped

        The code-import-controller daemon was shut-down, interrupting running
        jobs.
        """)

    QUIESCED = DBItem(120, """
        Quiesced

        The code-import-controller daemon has stopped accepting new jobs,
        completed running jobs, and then shut down.
        """)

    # Crash recovery

    WATCHDOG = DBItem(210, """
        Watchdog

        The watchdog has detected that the machine's heartbeat has not been
        updated recently.
        """)


class ICodeImportMachine(Interface):
    """A machine that can perform imports."""

    id = Int(readonly=True, required=True)

    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)

    hostname = TextLine(
        title=_('Host name'), required=True,
        description=_('The hostname of the machine.'))
    state = Choice(
        title=_('State'), required=True, vocabulary=CodeImportMachineState,
        default=CodeImportMachineState.OFFLINE,
        description=_("The state of the controller daemon on this machine."))
    heartbeat = Datetime(
        title=_("Heartbeat"),
        description=_("When the controller deamon last recorded it was"
                      " running."))

    def setOnline():
        """Set state to ONLINE, and record the corresponding event."""

    def setOffline(reason):
        """Set state to OFFLINE, and record the corresponding event.

        :param reason: CodeImportMachineOfflineReason enum value.
        """

    def setQuiescing(user, message):
        """Set state to QUIESCING, and record the corresponding event.

        :param user: `Person` that requested the machine to quiesce.
        :param message: user-provided message.
        """


class ICodeImportMachineSet(Interface):
    """The set of machines that can perform imports."""

    def getAll():
        """Return an iterable of all code machines."""

    def getByHostname(hostname):
        """Retrieve the code import machine for a hostname.

        Returns a `ICodeImportMachine` provider or ``None`` if no such machine
        is present.
        """
