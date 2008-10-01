# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database class to handle translation export view."""

__metaclass__ = type

__all__ = [
    'VPOExportSet',
    'VPOExport'
    ]

from zope.interface import implements

from canonical.database.sqlbase import sqlvalues, cursor
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.interfaces import IVPOExportSet, IVPOExport

class VPOExportSet:
    """Retrieve collections of `VPOExport` objects."""

    implements(IVPOExportSet)

    VIEW_NAME_PREFIX = 'POExport.' 
    column_names = [
        'potemplate',
        'template_header',
        'pofile',
        'language',
        'variant',
        'translation_file_comment',
        'translation_header',
        'is_translation_header_fuzzy',
        'potmsgset',
        'sequence',
        'comment',
        'source_comment',
        'file_references',
        'flags_comment',
        'context',
        'msgid_singular',
        'msgid_plural',
        'is_current',
        'is_imported',
        'translation0',
        'translation1',
        'translation2',
        'translation3',
        'translation4',
        'translation5',
    ]
    columns = ', '.join([ VIEW_NAME_PREFIX + name for name in column_names])

    # Obsolete translations are marked with a sequence number of 0, so they
    # would get sorted to the front of the file during export. To avoid that,
    # sequence numbers of 0 are translated to NULL and ordered to the end
    # with NULLS LAST so that they appear at the end of the file.
    # TODO: henninge 2008-10-01 spec=message-sharing-switchover: This will
    # change when message sharing is implemented, according to jtv.
    sort_column_names = [
        VIEW_NAME_PREFIX+'potemplate',
        VIEW_NAME_PREFIX+'language',
        VIEW_NAME_PREFIX+'variant',
        'CASE '
            'WHEN '+VIEW_NAME_PREFIX+'sequence = 0 THEN NULL '
            'ELSE '+VIEW_NAME_PREFIX+'sequence '
        'END NULLS LAST',
        VIEW_NAME_PREFIX+'id',
    ]
    sort_columns = ', '.join(sort_column_names)

    def _select(self, join=None, where=None):
        query = 'SELECT %s FROM POExport' % self.columns

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
                yield VPOExport(*row)
            else:
                break

    def get_pofile_rows(self, pofile):
        """See `IVPOExportSet`."""
        # Only fetch rows that belong to this POFile and are "interesting":
        # they must either be in the current template (sequence != 0, so not
        # "obsolete") or be in the current imported version of the translation
        # (is_imported), or both.
        where = """
            potemplate = %s AND
            language = %s AND
            (sequence <> 0 OR is_imported)
            """ % sqlvalues(pofile.potemplate, pofile.language)

        if pofile.variant:
            where += ' AND variant = %s' % sqlvalues(
                pofile.variant.encode('UTF-8'))
        else:
            where += ' AND variant is NULL'

        return self._select(where=where)

    def _get_distroseries_pofiles(self, series, date=None, component=None,
                                  languagepack=None):
        """Return a SQL query of PO files which would be contained in an
        export of a distribution series.

        The filtering is done based on the 'series', last modified 'date',
        archive 'component' and if it belongs to a 'languagepack'
        """
        join = '''
            FROM POFile
            JOIN POTemplate ON POTemplate.id = POFile.potemplate
            JOIN DistroSeries ON DistroSeries.id = POTemplate.distroseries
            '''

        where = '''
            WHERE
                DistroSeries.id = %s AND
                POTemplate.iscurrent IS TRUE
              ''' % sqlvalues(series)

        if date is not None:
            join += '''
                  JOIN TranslationMessage ON
                    TranslationMessage.pofile = POFile.id AND
                    TranslationMessage.is_current IS TRUE'''

            where += '''
                AND (TranslationMessage.date_reviewed > %s OR
                     POTemplate.date_last_updated > %s)''' % sqlvalues(
                    date, date)

        if component is not None:
            join += '''
            JOIN SourcePackagePublishingHistory ON
                SourcePackagePublishingHistory.distroseries=DistroSeries.id
            JOIN SourcePackageRelease ON
                SourcePackagePublishingHistory.sourcepackagerelease=
                     SourcePackageRelease.id
                  JOIN Component ON
                    SourcePackagePublishingHistory.component=Component.id
            '''

            where += '''
            AND SourcePackageRelease.sourcepackagename =
                POTemplate.sourcepackagename AND
            Component.name = %s AND
            SourcePackagePublishingHistory.dateremoved is NULL AND
            SourcePackagePublishingHistory.archive = %s
            ''' % sqlvalues(component, series.main_archive)

        if languagepack:
            where += ' AND POTemplate.languagepack'

        return join + where

    def get_distroseries_pofiles(self, series, date=None, component=None,
        languagepack=None):
        """See `IVPOExport`."""
        query_parts = [
            'SELECT DISTINCT POFile.id',
            self._get_distroseries_pofiles(
                series, date, component, languagepack),
            "ORDER BY POFile.id",
            ]

        cur = cursor()
        cur.execute('\n'.join(query_parts))
        for (id,) in cur.fetchall():
            yield POFile.get(id)

    def get_distroseries_pofiles_count(self, series, date=None,
                                        component=None, languagepack=None):
        """See `IVPOExport`."""
        query = self._get_distroseries_pofiles(
            series, date, component, languagepack)

        final_query = 'SELECT COUNT(DISTINCT POFile.id)\n' + query
        cur = cursor()
        cur.execute(final_query)
        value = cur.fetchone()
        return value[0]


class VPOExport:
    """Present Rosetta PO files in a form suitable for exporting them
    efficiently.
    """

    implements(IVPOExport)

    def __init__(self, *args):
        (potemplate,
         self.template_header,
         pofile,
         language,
         self.variant,
         self.translation_file_comment,
         self.translation_header,
         self.is_translation_header_fuzzy,
         potmsgset,
         self.sequence,
         self.comment,
         self.source_comment,
         self.file_references,
         self.flags_comment,
         self.context,
         self.msgid_singular,
         self.msgid_plural,
         self.is_current,
         self.is_imported,
         self.translation0,
         self.translation1,
         self.translation2,
         self.translation3,
         self.translation4,
         self.translation5) = args

        self.potemplate = POTemplate.get(potemplate)
        self.potmsgset = POTMsgSet.get(potmsgset)
        self.language = Language.get(language)
        if pofile is None:
            self.pofile = None
        else:
            self.pofile = POFile.get(pofile)
            if self.potmsgset.is_translation_credit:
                # Translation credits doesn't have plural forms so we only
                # update the singular one.
                self.translation0 = self.pofile.prepareTranslationCredits(
                    self.potmsgset)
