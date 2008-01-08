# Copyright 2005 Canonical Ltd. All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ('POExportRequestSet', 'POExportRequest')

from sqlobject import ForeignKey

from zope.interface import implements

from canonical.database.sqlbase import quote, SQLBase, sqlvalues
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    IPOExportRequestSet, IPOExportRequest, IPOTemplate, TranslationFileFormat)


class POExportRequestSet:
    implements(IPOExportRequestSet)

    @property
    def entry_count(self):
        """See `IPOExportRequestSet`."""
        return POExportRequest.select().count()

    def _addRequestEntry(
        self, person, potemplate, pofile, format, existing_requests):
        """Add a request entry to the queue.

        Requests that are already in existing_requests are silently ignored.

        :param existing_requests: a dict mapping templates to sets of
            previously requested `POFile`s translating those templates.  A
            `POFile` of None represents the template itself.
        """
        earlier_pofiles = existing_requests.get(potemplate)
        if earlier_pofiles is not None and pofile in earlier_pofiles:
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

        all_templates = set(potemplates)
        all_templates.update([pofile.potemplate for pofile in pofiles])
        potemplate_ids = ", ".join(
            [quote(template) for template in all_templates])
        # A null pofile stands for the template itself.  We represent it in
        # SQL as -1, because that's how it's indexed in the request table.
        pofile_ids = ", ".join([quote(pofile) for pofile in pofiles] + ["-1"])
        pofile_clause = "COALESCE(pofile, -1) IN (%s)" % pofile_ids

        persons_existing_requests = POExportRequest.select("""
            person = %s AND
            potemplate in (%s) AND
            %s AND
            format = %s
            """ % (
                quote(person), potemplate_ids, pofile_clause, quote(format)))

        existing_requests = {}
        for request in persons_existing_requests:
            if request.potemplate not in existing_requests:
                existing_requests[request.potemplate] = set()
            existing_requests[request.potemplate].add(request.pofile)

        for potemplate in potemplates:
            self._addRequestEntry(
                person, potemplate, None, format, existing_requests)

        for pofile in pofiles:
            self._addRequestEntry(
                person, pofile.potemplate, pofile, format, existing_requests)

    def popRequest(self):
        """See `IPOExportRequestSet`."""
        try:
            request = POExportRequest.select(limit=1, orderBy='id')[0]
        except IndexError:
            return None, None, None

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

