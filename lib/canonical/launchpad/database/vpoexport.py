# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Database class for Rosetta PO export view."""

__metaclass__ = type

__all__ = ['VPOExportSet', 'VPOExport']

from zope.interface import implements

from canonical.database.sqlbase import sqlvalues, cursor

from canonical.launchpad.database import POTemplate
from canonical.launchpad.database import POFile
from canonical.launchpad.database import Language
from canonical.launchpad.interfaces import IVPOExportSet, IVPOExport

class VPOExportSet:
    """Retrieve collections of VPOExport objects."""

    implements(IVPOExportSet)

    column_names = [
        'potemplate',
        'language',
        'variant',
        'potsequence',
        'posequence',
        'potheader',
        'poheader',
        'potopcomment',
        'pofuzzyheader',
        'isfuzzy',
        'activesubmission',
        'msgidpluralform',
        'translationpluralform',
        'msgid',
        'translation',
        'pocommenttext',
        'sourcecomment',
        'filereferences',
        'flagscomment',
    ]
    columns = ', '.join(['POExport.' + name for name in column_names])

    sort_column_names = [
        'potemplate',
        'language',
        'variant',
        'potsequence',
        'posequence',
        'msgidpluralform',
        'translationpluralform',
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

    def get_pofile_rows(self, potemplate, language, variant=None):
        """See IVPOExportSet."""
        where = ('potemplate = %s AND language = %s' %
            sqlvalues(potemplate.id, language.id))

        if variant:
            where += ' AND variant = %s' % sqlvalues(variant.encode('UTF-8'))

        return self._select(where=where)

    def get_potemplate_rows(self, potemplate):
        """See IVPOExportSet."""
        where = 'potemplate = %s' % sqlvalues(potemplate.id)
        return self._select(where=where)

    def _get_distrorelease_pofiles(self, release, date=None, component=None,
        languagepack=None):
        """Return a SQL query of PO files which would be contained in an
        export of a distribtuion release.

        The filtering is done based on the 'release', last modified 'date',
        archive 'component' and if it belongs to a 'languagepack'
        """
        join = '''
            FROM POFile
              JOIN POTemplate ON POTemplate.id = POFile.potemplate
              JOIN DistroRelease ON
                DistroRelease.id = POTemplate.distrorelease'''

        where = '''
            WHERE
              DistroRelease.id = %s''' % sqlvalues(release.id)

        if date is not None:
            join += '''
                  JOIN POMsgSet ON POMsgSet.pofile = POFile.id
                  JOIN POSelection ON POSelection.pomsgset = POMsgSet.id
                  JOIN POSubmission ON
                    POSubmission.id = POSelection.activesubmission'''

            where += ''' AND
                  POSubmission.datecreated > %s
                ''' % sqlvalues(date)

        if component is not None:
            join += '''
                  JOIN SourcePackagePublishing ON
                    SourcePackagePublishing.distrorelease=DistroRelease.id
                  JOIN SourcePackageRelease ON
                    SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id
                  JOIN Component ON
                    SourcePackagePublishing.component=Component.id'''

            where += ''' AND
                SourcePackageRelease.sourcepackagename = POTemplate.sourcepackagename AND
                Component.name = %s''' % sqlvalues(component)

        if languagepack is not None:
            where += ''' AND
                POTemplate.languagepack = %s''' % sqlvalues(languagepack)

        return join + where

    def get_distrorelease_pofiles(self, release, date=None, component=None,
        languagepack=None):
        """See IVPOExport."""
        query = self._get_distrorelease_pofiles(
            release, date, component, languagepack)

        final_query = 'SELECT DISTINCT POFile.id\n' + query
        cur = cursor()
        cur.execute(final_query)
        for (id,) in cur.fetchall():
            yield POFile.get(id)

    def get_distrorelease_pofiles_count(self, release, date=None, component=None,
        languagepack=None):
        """See IVPOExport."""
        query = self._get_distrorelease_pofiles(
            release, date, component, languagepack)

        final_query = 'SELECT COUNT(DISTINCT POFile.id)\n' + query
        cur = cursor()
        cur.execute(final_query)
        value = cur.fetchone()
        return value[0]

    def get_distrorelease_rows(self, release, date=None):
        """See IVPOExportSet."""

        if date is None:
            join = None
            where = ('distrorelease = %s AND languagepack = True' %
                    sqlvalues(release.id))
        else:
            join = [
                'POFile ON POFile.id = POExport.pofile',
                'POTemplate ON POFile.potemplate = POTemplate.id',
                'POMsgSet ON POMsgSet.pofile = POFile.id',
                'POSelection ON POMsgSet.id = POSelection.pomsgset',
                'POSubmission ON '
                    'POSubmission.id = POSelection.activesubmission',
            ]
            where = '''
                 POSubmission.datecreated > %s AND
                 POTemplate.distrorelease = %s
            ''' % sqlvalues(date, release.id)

        return self._select(join=join, where=where)


class VPOExport:
    """Present Rosetta PO files in a form suitable for exporting them
    efficiently.
    """

    implements(IVPOExport)

    def __init__(self, *args):
        (self.potemplate,
         language,
         self.variant,
         self.potsequence,
         self.posequence,
         self.potheader,
         self.poheader,
         self.potopcomment,
         self.pofuzzyheader,
         self.isfuzzy,
         self.activesubmission,
         self.msgidpluralform,
         self.translationpluralform,
         self.msgid,
         self.translation,
         self.pocommenttext,
         self.sourcecomment,
         self.filereferences,
         self.flagscomment) = args

        self.language = Language.get(language)
        self.pofile = POFile.selectOneBy(
            potemplateID=self.potemplate,
            languageID=language,
            variant=self.variant)

