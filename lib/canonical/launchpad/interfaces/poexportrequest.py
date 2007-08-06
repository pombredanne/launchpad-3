# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

__all__ = ('IPOExportRequestSet', 'IPOExportRequest')

from zope.interface import Interface, Attribute
from zope.schema import Int
from canonical.lp.dbschema import TranslationFileFormat

class IPOExportRequestSet(Interface):
    number_entries = Int(
        title=u'Number of entries waiting in the queue.',
        required=True, readonly=True)

    def addRequest(person, potemplate=None, pofiles=None,
                   format=TranslationFileFormat.PO):
        """Add a request to export a set of files.

        :param potemplate: The PO template to export, or `None`.
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

