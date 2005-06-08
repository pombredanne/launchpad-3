# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

__all__ = ('IPOExportRequestSet', 'IPOExportRequest')

from zope.interface import Interface, Attribute

class IPOExportRequestSet(Interface):
    def addRequest(self, person, potemplate, pofiles):
        """Add a request to export a set of files.

        :potemplate: The PO template to export, or None.
        :pofiles: A list of PO files to export.
        """

    def popRequest(self):
        """Take the next request out of the queue.

        Returns a 3-tuple containing the person who made the request, the PO
        template the request was for, and a list of POTemplate and POFile
        objects to export.
        """

class IPOExportRequest(Interface):
    person = Attribute("The person who made the request.")
    potemplate = Attribute(
        "The PO template to which the requested files belong.")
    pofile = Attribute(
        "The PO file requested, if any.")

