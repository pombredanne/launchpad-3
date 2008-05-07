# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Code import machine interfaces."""

__metaclass__ = type

__all__ = [
    'ICodeImportMachine',
    'ICodeImportMachineSet',
    'CodeImportMachineOfflineReason',
    'CodeImportMachineState',
    ]

from zope.interface import Attribute, Interface
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

    A machine goes offline when a code-import-controller daemon process shuts
    down, or appears to have crashed. Recording the reason a machine went
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

        The code-import-controller daemon has shut down after completing
        any running jobs.
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

    state = Choice(
        title=_('State'), required=True, vocabulary=CodeImportMachineState,
        default=CodeImportMachineState.OFFLINE,
        description=_("The state of the controller daemon on this machine."))

    hostname = TextLine(
        title=_('Host name'), required=True,
        description=_('The hostname of the machine.'))

    current_jobs = Attribute(
        'The current jobs that the machine is processing.')

    events = Attribute(
        'The events associated with this machine.')

    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)

    heartbeat = Datetime(
        title=_("Heartbeat"),
        description=_("When the controller deamon last recorded it was"
                      " running."))

    def setOnline(user=None, message=None):
        """Record that the machine is online, marking it ready to accept jobs.

        Set state to ONLINE, and record the corresponding event.
        :param user: `Person` that requested going online if done by a user.
        :param message: User-provided message.
        """

    def setOffline(reason, user=None, message=None):
        """Record that the machine is offline.

        Set state to OFFLINE, and record the corresponding event.

        :param reason: `CodeImportMachineOfflineReason` enum value.
        :param user: `Person` that requested going online if done by a user.
        :param message: User-provided message.
        """

    def setQuiescing(user, message=None):
        """Initiate an orderly shut down without interrupting running jobs.

        Set state to QUIESCING, and record the corresponding event.

        :param user: `Person` that requested the machine to quiesce.
        :param message: User-provided message.
        """


class ICodeImportMachineSet(Interface):
    """The set of machines that can perform imports."""

    def __getitem__(hostname):
        """Retrieve a code import machine by hostname."""

    def getAll():
        """Return an iterable of all code machines."""

    def new(hostname):
        """Create a new CodeImportMachine.

        The machine will initially be in the 'OFFLINE' state.
        """

    def getByHostname(hostname):
        """Retrieve the code import machine for a hostname.

        Returns a `ICodeImportMachine` provider or ``None`` if no such machine
        is present.
        """
