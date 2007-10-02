# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['CodeImportJobStatus', 'ICodeImportJob', 'ICodeImportJobSet']

from canonical.launchpad.interfaces.codeimport import ICodeImport
from canonical.launchpad.interfaces.codeimportmachine import ICodeImportMachine
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr import (
    DBEnumeratedType, DBItem)

from zope.interface import Interface
from zope.schema import Choice, Datetime, Int, Object, Text

class CodeImportJobStatus(DBEnumeratedType):
    pass

class ICodeImportJob(Interface):
    """A pending or active code import job.

    There is always such a row for any active import, but it will not
    run until date_due is in the past."""

    id = Int()
    code_import = Object(schema=ICodeImport)
    machine = Object(schema=ICodeImportMachine)
    date_due = Datetime()
    state = Choice(vocabulary=CodeImportJobStatus)
    requesting_user = Object(schema=IPerson)
    ordering = Int()
    heartbeat = Datetime()
    logtail = Text()
    date_started = Datetime()



class ICodeImportJobSet(Interface):
    """XXX"""


