# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Database class to handle translation export view."""

__metaclass__ = type

__all__ = [
    'VPOExportSet',
    'VPOExport'
    ]

from zope.interface import implements

from canonical.database.sqlbase import sqlvalues, cursor
from canonical.launchpad.database import Language
from canonical.launchpad.database import POFile
from canonical.launchpad.database import POTemplate
from canonical.launchpad.database import POTMsgSet
from canonical.launchpad.interfaces import IVPOExportSet, IVPOExport

class VPOExportSet:
    """Retrieve collections of VPOExport objects."""

    implements(IVPOExportSet)

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
        'is_fuzzy',
        'is_current',
        'is_imported',
        'translation0',
        'translation1',
        'translation2',
        'translation3',
    ]
    columns = ', '.join(['POExport.' + name for name in column_names])

    sort_column_names = [
        'potemplate',
        'language',
        'variant',
        'sequence',
        'id',
    ]
    sort_columns = ', '.join(
        ['POExport.' + name for name in sort_column_names])

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
        """See IVPOExportSet."""
        where = ('potemplate = %s AND language = %s' %
            sqlvalues(pofile.potemplate, pofile.language))

        if pofile.variant:
            where += ' AND variant = %s' % sqlvalues(
                pofile.variant.encode('UTF-8'))
        else:
            where += ' AND variant is NULL'

        return self._select(where=where)

    def get_potemplate_rows(self, potemplate):
        """See IVPOExportSet."""
        where = 'potemplate = %s' % sqlvalues(potemplate.id)

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
              JOIN DistroRelease ON
                DistroRelease.id = POTemplate.distrorelease'''

        where = '''
            WHERE
              DistroRelease.id = %s
              ''' % sqlvalues(series)

        if date is not None:
            join += '''
                  JOIN TranslationMessage ON
                    TranslationMessage.pofile = POFile.id AND
                    TranslationMessage.date_reviewed > %s AND
                    TranslationMessage.is_current IS TRUE''' % sqlvalues(date)

        if component is not None:
            join += '''
            JOIN SourcePackagePublishingHistory ON
                SourcePackagePublishingHistory.distrorelease=DistroRelease.id
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
        """See IVPOExport."""
        query = self._get_distroseries_pofiles(
            series, date, component, languagepack)

        final_query = 'SELECT DISTINCT POFile.id\n' + query
        cur = cursor()
        cur.execute(final_query)
        for (id,) in cur.fetchall():
            yield POFile.get(id)

    def get_distroseries_potemplates(self, series, component=None,
        languagepack=None):
        """Return a SQL query of PO files which would be contained in an
        export of a distribtuion series.

        The filtering is done based on the 'series', last modified 'date',
        archive 'component' and if it belongs to a 'languagepack'
        """
        join = '''
            SELECT DISTINCT POTemplate.id
            FROM POTemplate
              JOIN DistroRelease ON
                DistroRelease.id = POTemplate.distrorelease'''

        where = '''
            WHERE
              DistroSeries.id = %s
              ''' % sqlvalues(series)

        if component is not None:
            join += '''
            JOIN SourcePackagePublishingHistory ON
                SourcePackagePublishingHistory.distrorelease =
                    DistroRelease.id
            JOIN SourcePackageRelease ON
                SourcePackagePublishingHistory.sourcepackagerelease =
                    SourcePackageRelease.id
            JOIN Component ON
                SourcePackagePublishingHistory.component=Component.id
            '''

            where += ''' AND
                SourcePackageRelease.sourcepackagename =
                    POTemplate.sourcepackagename AND
                Component.name = %s AND
                SourcePackagePublishingHistory.dateremoved is NULL AND
                SourcePackagePublishingHistory.archive = %s
                ''' % sqlvalues(component, series.main_archive)

        if languagepack:
            where += ' AND POTemplate.languagepack'

        cur = cursor()
        cur.execute(join + where)
        for (id,) in cur.fetchall():
            yield POTemplate.get(id)

    def get_distroseries_pofiles_count(self, series, date=None,
                                        component=None, languagepack=None):
        """See IVPOExport."""
        query = self._get_distroseries_pofiles(
            series, date, component, languagepack)

        final_query = 'SELECT COUNT(DISTINCT POFile.id)\n' + query
        cur = cursor()
        cur.execute(final_query)
        value = cur.fetchone()
        return value[0]

    def get_distroseries_rows(self, series, date=None):
        """See IVPOExportSet."""

        if date is None:
            join = None
            where = ('distrorelease = %s AND languagepack' %
                    sqlvalues(series.id))
        else:
            join = [
                'POFile ON POFile.id = POExport.pofile',
                'POTemplate ON POFile.potemplate = POTemplate.id',
                'TranslationMessage ON '
                    'TranslationMessage.pofile = POFile.id AND '
                    'TranslationMessage.date_reviewed > %s AND '
                    'TranslationMessage.is_current IS TRUE' % sqlvalues(date),
            ]
            where = 'POTemplate.distrorelease = %s' % sqlvalues(series)

        return self._select(join=join, where=where)


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
         self.is_fuzzy,
         self.is_current,
         self.is_imported,
         self.translation0,
         self.translation1,
         self.translation2,
         self.translation3) = args

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
