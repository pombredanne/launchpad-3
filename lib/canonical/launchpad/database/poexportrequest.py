# Copyright 2005-2008 Canonical Ltd. All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ('POExportRequestSet', 'POExportRequest')

from sqlobject import ForeignKey

from zope.interface import implements

from canonical.database.sqlbase import cursor, quote, SQLBase, sqlvalues
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    IPOExportRequestSet, IPOExportRequest, IPOTemplate, TranslationFileFormat)
from canonical.launchpad.validators.person import public_person_validator


class POExportRequestSet:
    implements(IPOExportRequestSet)

    @property
    def entry_count(self):
        """See `IPOExportRequestSet`."""
        return POExportRequest.select().count()

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

        potemplate_ids = ", ".join(
            [quote(template) for template in potemplates])
        # A null pofile stands for the template itself.  We represent it in
        # SQL as -1, because that's how it's indexed in the request table.
        pofile_ids = ", ".join([quote(pofile) for pofile in pofiles] + ["-1"])

        query_params = {
            'person': quote(person),
            'format': quote(format),
            'templates': potemplate_ids,
            'pofiles': pofile_ids,
            }

        cur = cursor()

        if potemplates:
            # Create requests for all these templates, insofar as the same
            # user doesn't already have requests pending for them in the same
            # format.
            cur.execute("""
                INSERT INTO POExportRequest(person, potemplate, format)
                SELECT %(person)s, template.id, %(format)s
                FROM POTemplate AS template
                LEFT JOIN POExportRequest AS existing ON
                    existing.person = %(person)s AND
                    existing.potemplate = template.id AND
                    existing.pofile IS NULL AND
                    existing.format = %(format)s
                WHERE
                    template.id IN (%(templates)s) AND
                    existing.id IS NULL
            """ % query_params)

        if pofiles:
            # Create requests for all these translations, insofar as the same
            # user doesn't already have identical requests pending.
            cur.execute("""
                INSERT INTO POExportRequest(
                    person, potemplate, pofile, format)
                SELECT %(person)s, template.id, pofile.id, %(format)s
                FROM POFile
                JOIN POTemplate AS template ON template.id = POFile.potemplate
                LEFT JOIN POExportRequest AS existing ON
                    existing.person = %(person)s AND
                    existing.pofile = POFile.id AND
                    existing.format = %(format)s
                WHERE
                    POFile.id IN (%(pofiles)s) AND
                    existing.id IS NULL
                """ % query_params)

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

    person = ForeignKey(
        dbName='person', foreignKey='Person',
        validator=public_person_validator, notNull=True)
    potemplate = ForeignKey(dbName='potemplate', foreignKey='POTemplate',
        notNull=True)
    pofile = ForeignKey(dbName='pofile', foreignKey='POFile')
    format = EnumCol(dbName='format', schema=TranslationFileFormat,
        default=TranslationFileFormat.PO, notNull=True)

