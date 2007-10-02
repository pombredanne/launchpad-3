# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'CodeImportResultStatus', 'ICodeImportResult', 'ICodeImportResultSet']

from canonical.launchpad.interfaces.codeimport import ICodeImport
from canonical.launchpad.interfaces.codeimportmachine import ICodeImportMachine
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr import (
    DBEnumeratedType, DBItem)

from zope.interface import Interface
from zope.schema import Choice, Datetime, Int, Object, Text


class CodeImportResultStatus(DBEnumeratedType):
    """XXX."""


class ICodeImportResult(Interface):
    """XXX."""

    id = Int()
    date_created = Datetime()
    code_import = Object(schema=ICodeImport)
    machine = Object(schema=ICodeImportMachine)
    requesting_user = Object(schema=IPerson)
    logtail = Text()
    log_file = Object(schema=ILibraryFileAlias)
    status = Choice(vocabulary=CodeImportResultStatus)
    date_started = Datetime()


class ICodeImportResultSet(Interface):
    """XXX."""
