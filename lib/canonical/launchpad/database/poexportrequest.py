# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type

__all__ = ('POExportRequestSet', 'POExportRequest')

from sqlobject import ForeignKey

from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IPOExportRequestSet, \
    IPOExportRequest

class POExportRequestSet:
    implements(IPOExportRequestSet)

    def addRequest(self, person, potemplate, pofiles):
        """See IPOExportRequestSet."""

        if not (potemplate or pofiles):
            raise ValueError(
                "Can't add a request with no PO template and no PO files")

        if potemplate:
            POExportRequest(
                person=person,
                potemplate=potemplate,
                pofile=None)

        for pofile in pofiles:
            POExportRequest(
                person=person,
                potemplate=pofile.potemplate,
                pofile=pofile)

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
        objects = []

        for request in requests:
            if request.pofile is not None:
                objects.append(request.pofile)
            else:
                objects.append(request.potemplate)

            POExportRequest.delete(request.id)

        return person, potemplate, objects

class POExportRequest(SQLBase):
    implements(IPOExportRequest)

    _table = 'POExportRequest'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    potemplate = ForeignKey(dbName='potemplate', foreignKey='POTemplate',
        notNull=True)
    pofile = ForeignKey(dbName='pofile', foreignKey='POFile')

