# Copyright 2007 Canonical Ltd. All rights reserved.

__metaclass__ = type

__all__ = ('IPOExportRequestSet', 'IPOExportRequest')

from zope.interface import Interface, Attribute
from canonical.lp.dbschema import TranslationFileFormat

class IPOExportRequestSet(Interface):
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
    person = Attribute("The person who made the request.")
    potemplate = Attribute(
        "The PO template to which the requested files belong.")
    pofile = Attribute(
        "The PO file requested, if any.")

