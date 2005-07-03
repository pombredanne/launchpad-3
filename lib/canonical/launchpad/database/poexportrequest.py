# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

__all__ = ('POExportRequestSet', 'POExportRequest')

from sqlobject import ForeignKey

from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IPOExportRequestSet, \
    IPOExportRequest
from canonical.lp.dbschema import EnumCol, RosettaFileFormat

class POExportRequestSet:
    implements(IPOExportRequestSet)

    def _addRequestEntry(self, person, potemplate, pofile, format):
        """Add a request entry to the queue.

        Duplicate requests are silently ignored.
        """

        if pofile:
            pofileID = pofile.id
        else:
            pofileID = None

        request = POExportRequest.selectOneBy(
            personID=person.id,
            potemplateID=potemplate.id,
            pofileID=pofileID,
            format=format)

        if request is not None:
            return

        POExportRequest(
            person=person,
            potemplate=potemplate,
            pofile=pofile,
            format=format)

    def addRequest(self, person, potemplate=None, pofiles=[],
            format=RosettaFileFormat.PO):
        """See IPOExportRequestSet."""

        if not (potemplate or pofiles):
            raise ValueError(
                "Can't add a request with no PO template and no PO files")

        if potemplate:
            self._addRequestEntry(person, potemplate, None, format)

        for pofile in pofiles:
            self._addRequestEntry(person, pofile.potemplate, pofile, format)

    def popRequest(self):
        """See IPOExportRequestSet."""

        try:
            request = POExportRequest.select(limit=1, orderBy='id')[0]
        except IndexError:
            return None

        # The list() is a workaround used to prevent warnings about indexing
        # an unordered set being unreliable.

        requests = list(POExportRequest.selectBy(
            personID=request.person.id, potemplateID=request.potemplate.id))
        person = requests[0].person
        potemplate = requests[0].potemplate
        format = requests[0].format
        objects = []

        for request in requests:
            if request.pofile is not None:
                objects.append(request.pofile)
            else:
                objects.append(request.potemplate)

            POExportRequest.delete(request.id)

        return person, potemplate, objects, format

class POExportRequest(SQLBase):
    implements(IPOExportRequest)

    _table = 'POExportRequest'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    potemplate = ForeignKey(dbName='potemplate', foreignKey='POTemplate',
        notNull=True)
    pofile = ForeignKey(dbName='pofile', foreignKey='POFile')
    format = EnumCol(dbName='format', schema=RosettaFileFormat,
        default=RosettaFileFormat.PO, notNull=True)

