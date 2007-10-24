# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database class for Rosetta POT export view."""

__metaclass__ = type

__all__ = ['VPOTExportSet', 'VPOTExport']

from zope.interface import implements

from canonical.database.sqlbase import sqlvalues, cursor

from canonical.launchpad.database import POTemplate
from canonical.launchpad.interfaces import IVPOTExportSet, IVPOTExport

class VPOTExportSet:
    """Retrieve collections of VPOTExport objects."""

    implements(IVPOTExportSet)

    column_names = [
        'potemplate',
        'sequence',
        'header',
        'context',
        'msgid_singular',
        'msgid_plural',
        'comment_text',
        'source_comment',
        'file_references',
        'flags_comment',
    ]
    columns = ', '.join(['POTExport.' + name for name in column_names])

    sort_column_names = [
        'potemplate',
        'sequence',
        'potmsgset',
    ]
    sort_columns = ', '.join(
        ['POTExport.' + name for name in sort_column_names])

    def _select(self, join=None, where=None):
        query = 'SELECT %s FROM POTExport' % self.columns

        if join is not None:
            query += ''.join([' JOIN ' + s for s in join])

        if where is not None:
            query += ' WHERE %s' % where

        query += ' ORDER BY %s' % self.sort_columns

        cur = cursor()
        cur.execute(query)

        while True:
            row = cur.fetchone()

            if row is not None:
                yield VPOTExport(*row)
            else:
                break

    def get_potemplate_rows(self, potemplate):
        """See IVPOTExportSet."""
        where = 'potemplate = %s' % sqlvalues(potemplate.id)

        return self._select(where=where)


class VPOTExport:
    """Present Rosetta POT files in a form suitable for exporting them
    efficiently.
    """

    implements(IVPOTExport)

    def __init__(self, *args):
        (potemplate,
         self.sequence,
         self.header,
         self.context,
         self.msgid_singular,
         self.msgid_plural,
         self.comment_text,
         self.source_comment,
         self.file_references,
         self.flags_comment) = args

        self.potemplate = POTemplate.get(potemplate)

