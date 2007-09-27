# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

__all__ = ('POExportRequestSet', 'POExportRequest')

from sqlobject import ForeignKey

from zope.interface import implements

from canonical.database.sqlbase import (SQLBase, sqlvalues)
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    IPOExportRequestSet, IPOExportRequest, IPOTemplate, TranslationFileFormat)


class POExportRequestSet:
    implements(IPOExportRequestSet)

    @property
    def entry_count(self):
        """See `IPOExportRequestSet`."""
        return POExportRequest.select().count()

    def _addRequestEntry(self, person, potemplate, pofile, format):
        """Add a request entry to the queue.

        Duplicate requests are silently ignored.
        """

        request = POExportRequest.selectOneBy(
            person=person, potemplate=potemplate, pofile=pofile, format=format)

        if request is not None:
            return

        request = POExportRequest(
            person=person,
            potemplate=potemplate,
            pofile=pofile,
            format=format)

    def addRequest(self, person, potemplates=None, pofiles=None,
            format=TranslationFileFormat.PO):
        """See `IPOExportRequestSet`."""
        if potemplates is None:
            potemplates = []
        elif IPOTemplate.providedBy(potemplates):
            # Allow single POTemplate as well as list of POTemplates
            potemplates = [potemplates]
        if pofiles is None:
            pofiles = []

        if not (potemplates or pofiles):
            raise AssertionError(
                "Can't add a request with no PO templates and no PO files.")

        for potemplate in potemplates:
            self._addRequestEntry(person, potemplate, None, format)

        for pofile in pofiles:
            self._addRequestEntry(person, pofile.potemplate, pofile, format)

    def popRequest(self):
        """See `IPOExportRequestSet`."""
        try:
            request = POExportRequest.select(limit=1, orderBy='id')[0]
        except IndexError:
            return None

        person = request.person
        format = request.format

        query = """
            person = %s AND
            format = %s AND
            date_created = (
                SELECT date_created
                FROM POExportRequest
                ORDER BY id
                LIMIT 1)""" % sqlvalues(person, format)
        requests = POExportRequest.select(query, orderBy='potemplate')
        objects = []

        for request in requests:
            if request.pofile is not None:
                objects.append(request.pofile)
            else:
                objects.append(request.potemplate)

            POExportRequest.delete(request.id)

        return person, objects, format


class POExportRequest(SQLBase):
    implements(IPOExportRequest)

    _table = 'POExportRequest'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    potemplate = ForeignKey(dbName='potemplate', foreignKey='POTemplate',
        notNull=True)
    pofile = ForeignKey(dbName='pofile', foreignKey='POFile')
    format = EnumCol(dbName='format', schema=TranslationFileFormat,
        default=TranslationFileFormat.PO, notNull=True)

