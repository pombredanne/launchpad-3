# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Code import audit trail interfaces."""

__metaclass__ = type
__all__ = [
    'CodeImportEventDataType',
    'CodeImportEventType',
    'ICodeImportEvent',
    'ICodeImportEventSet',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Choice, Int

from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem


class CodeImportEventType(DBEnumeratedType):
    """CodeImportEvent type.

    Event types identify all the events that are significant to the code
    import system. Either user-driven events, or events recording the
    operation of unattended systems.
    """

    # Event types are named so that "a FOO event" sounds natural. For example,
    # MODIFY because "a MODIFIED event" sounds confusing and "a MODIFICATION
    # event" is awkyard.

    # Code import life cycle.

    CREATE = DBItem(110, """Import Created

    A CodeImport object was created.
    """)

    MODIFY = DBItem(120, """Import Modified

    A code import was modified. Either the CodeImport object, or an associated
    object was modified.
    """)

    DELETE = DBItem(130, """Import Deleted

    A CodeImport object was deleted.
    """)

    # Code import job events.

    START = DBItem(210, """Job Started

    An import job was started.
    """)

    FINISH = DBItem(220, """Job Finished

    An import job finished, either successfully or by a failure.
    """)

    PUBLISH = DBItem(230, """Import First Published

    A code import has completed for the first time and was published.
    """)

    RECLAIM = DBItem(240, """Job Reclaimed Automatically

    A code import job has not finished, but has probably crashed and is
    allowed to run again.
    """)

    # Code import job control events.

    REQUEST = DBItem(310, """Update Requested

    A user requested that an import job be run immediately.
    """)

    KILL = DBItem(320, """Termination Requested

    A user requested that a running import job be aborted.
    """)

    # Code import machine events.

    ONLINE = DBItem(410, """Machine Online

    A code-import-controller daemon has started and is now accepting jobs.
    """)

    OFFLINE = DBItem(420, """Machine Offline

    A code-import-controller daemon has finished or crashed is and no longer
    running.
    """)

    QUIESCE = DBItem(430, """Quiescing Requested

    A code-import-controller daemon has been requested to shut down. It will
    no longer accept jobs and will terminate once the last running job
    finishes.
    """)


class CodeImportEventDataType(DBEnumeratedType):
    """CodeImportEventData type.

    CodeImportEvent objects record unstructured additional data. Each data item
    associated to an event has a type from this enumeration.
    """

    # CodeImport attributes

    CODE_IMPORT = DBItem(110, """Code Import

    Database id of the CodeImport, useful to collate events associated to
    deleted CodeImport objects.
    """)

    BRANCH = DBItem(120, """Branch

    Value of CodeImport.branch. Useful if the CodeImport was deleted.
    """)

    OWNER = DBItem(130, """Code Import Owner

    Value of CodeImport.owner. Useful to record ownership changes.
    """)

    REVIEW_STATUS = DBItem(140, """Review Status

    Value of CodeImport.review_status. Useful to understand the review life
    cycle of a code import.
    """)

    ASSIGNEE = DBItem(150, """Code Import Assignee

    Value of CodeImport.assignee. Useful to understand the review life cycle of
    a code import.
    """)

    # CodeImport attributes related to the import source

    UPDATE_INTERVAL = DBItem(210, """Update Interval

    User-specified interval between updates of the code import.
    """)

    CVS_ROOT = DBItem(220, """CVSROOT

    Location and access method of the CVS repository.
    """)

    CVS_MODULE = DBItem(221, """CVS module

    Path to import within the CVSROOT.
    """)

    SVN_BRANCH_URL = DBItem(230, """Subversion URL

    Location of the Subversion branch to import.
    """)


class ICodeImportEvent(Interface):
    """One event in the code-import audit trail."""

    id = Int(readonly=True, required=True)
    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)

    event_type = Choice(
        title=_("Event"), required=True, readonly=True,
        vocabulary=CodeImportEventType,
        description=_("The type of this event."""))
    code_import = Choice(
        title=_("Code Import"), required=False, readonly=True,
        vocabulary='CodeImport',
        description=_("The code import affected by this event."""))
    person = Choice(
        title=_("Person"), required=False, readonly=True,
        vocabulary='Person',
        description=_("The person that triggered this event."""))
    machine = Choice(
        title=_("Machine"), required=False, readonly=True,
        vocabulary='CodeImportMachine',
        description=_("The import machine where this event occured."""))

    def items():
        """List of key-value tuples recording additional information.

        Keys are values from the CodeImportEventDataType enum, values are
        strings or None.
        """

class ICodeImportEventSet(Interface):
    """The set of all CodeImportEvent objects."""

    def getAll():
        """Iterate over all `CodeImportEvent` objects.

        For use only in tests.
        """

    def getEventsForCodeImport(code_import):
        """Iterate over `CodeImportEvent` objects associated to a CodeImport.
        """

    def newCreate(code_import, person):
        """Record the creation of a `CodeImport` object.

        Should only be called by CodeImportSet.new.

        :param code_import: Newly created `CodeImport` object.
        :param user: User that created the object, usually the view's user.
        :return: `CodeImportEvent` with type CREATE.
        """
