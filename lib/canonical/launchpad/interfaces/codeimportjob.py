# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['CodeImportJobState', 'ICodeImportJob', 'ICodeImportJobSet']

from canonical.launchpad.interfaces.codeimport import ICodeImport
from canonical.launchpad.interfaces.codeimportmachine import ICodeImportMachine
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr import (
    DBEnumeratedType, DBItem)

from zope.interface import Interface
from zope.schema import Choice, Datetime, Int, Object, Text


class CodeImportJobState(DBEnumeratedType):
    PENDING = DBItem(10, """
        Pending

        The job has a time when it is due to run, and will wait until
        that time or an explicit update request is made.
        """)

    SCHEDULED = DBItem(20, """
        Scheduled

        The job is due to be run.
        """)

    RUNNING = DBItem(30, """
        Running

        The job is running.
        """)


class ICodeImportJob(Interface):
    """A pending or active code import job.

    There is always such a row for any active import, but it will not
    run until date_due is in the past."""

    id = Int()
    date_created = Datetime()
    code_import = Object(schema=ICodeImport)
    machine = Object(schema=ICodeImportMachine)
    date_due = Datetime()
    state = Choice(vocabulary=CodeImportJobState)
    requesting_user = Object(schema=IPerson)
    ordering = Int()
    heartbeat = Datetime()
    logtail = Text()
    date_started = Datetime()


class ICodeImportJobSet(Interface):
    """XXX."""

    def new(code_import):
        """XXX."""
