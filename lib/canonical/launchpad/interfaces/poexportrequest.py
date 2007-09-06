# Copyright 2007 Canonical Ltd. All rights reserved.

__metaclass__ = type

__all__ = [
    'IPOExportRequestSet',
    'IPOExportRequest'
    ]

from zope.interface import Interface
from zope.schema import Int, Object

from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces.pofile import IPOFile
from canonical.launchpad.interfaces.potemplate import IPOTemplate
from canonical.lp.dbschema import TranslationFileFormat

class IPOExportRequestSet(Interface):
    entry_count = Int(
        title=u'Number of entries waiting in the queue.',
        required=True, readonly=True)

    def addRequest(person, potemplates=None, pofiles=None,
                   format=TranslationFileFormat.PO):
        """Add a request to export a set of files.

        :param potemplates: PO template or list of PO templates to export, or
            `None`.
        :param pofiles: A list of PO files to export.
        """

    def popRequest():
        """Take the next request out of the queue.

        Returns a 3-tuple containing the person who made the request, the PO
        template the request was for, and a list of `POTemplate` and `POFile`
        objects to export.
        """

class IPOExportRequest(Interface):
    person = Object(
        title=u'The person who made the request.',
        required=True, readonly=True, schema=IPerson)

    potemplate = Object(
        title=u'The translation template to which the requested file belong.',
        required=True, readonly=True, schema=IPOTemplate)

    pofile = Object(
        title=u'The translation file requested, if any.',
        required=True, readonly=True, schema=IPOFile)

