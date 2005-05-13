# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Database class for Rosetta PO export view."""

__metaclass__ = type

__all__ = ['VPOExportSet', 'VPOExport']

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol

from zope.interface import implements

from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.launchpad.interfaces import IVPOExportSet
from canonical.launchpad.interfaces import IVPOExport


class VPOExportSet:
    """Retrieve collections of VPOExport objects."""

    implements(IVPOExportSet)
    columns = [
        'potemplate',
        'language',
        'variant',
        'potsequence',
        'posequence',
        'msgidpluralform',
        'translationpluralform',
        ]

    def get_pofile_rows(self, potemplate, language, variant=None):
        """See IVPOExportSet."""

        clauses = {
            'potemplateID': potemplate.id,
            'languageID': language.id,
            'orderBy': VPOExportSet.columns,
            }

        if variant:
            clauses['variant'] = variant

        return VPOExport.selectBy(**clauses)

    def get_potemplate_rows(self, potemplate):
        """See IVPOExportSet."""
        return VPOExport.selectBy(potemplateID=potemplate.id,
            orderBy=VPOExportSet.columns)

    def get_distrorelease_rows(self, release, date=None):
        """See IVPOExportSet."""

        if date is None:
            return VPOExport.selectBy(distroreleaseID=release.id,
                orderBy=VPOExportSet.columns, languagepack=True)
        else:
            return VPOExport.select('''
                pofile IN (
                     SELECT POFile.id
                     FROM POFile
                     JOIN POTemplate ON POFile.potemplate = POTemplate.id
                     JOIN POMsgSet ON POMsgSet.pofile = POFile.id
                     JOIN POTranslationSighting
                        ON POMsgSet.id = POTranslationSighting.pomsgset
                     WHERE
                         POTranslationSighting.datelastactive > %s AND
                         POTemplate.distrorelease = %s
                )
                ''' % sqlvalues(date, release.id))



class VPOExport(SQLBase):
    """Present Rosetta PO files in a form suitable for exporting them
    efficiently.
    """
    implements(IVPOExport)

    _idType = str
    _table = 'POExport'

    # POTemplateName.name
    name = StringCol(dbName='name')
    # POTemplateName.translationdomain
    translationdomain = StringCol(dbName='translationdomain')

    # POTemplate.id
    potemplate = ForeignKey(foreignKey='POTemplate', dbName='potemplate')
    # POTemplate.distrorelease
    distrorelease = ForeignKey(foreignKey='DistroRelease',
        dbName='distrorelease')
    # POTemplate.sourcepackagename
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename')
    # POTemplate.productrelease
    productrelease = ForeignKey(foreignKey='ProductRelease',
        dbName='productrelease')
    # POTemplate.header
    potheader = StringCol(dbName='potheader')
    # POTemplate.languagepack
    languagepack = BoolCol(dbName='languagepack')

    # POFile.id
    pofile = IntCol(dbName='pofile')
    # POFile.language
    language = ForeignKey(foreignKey='Language', dbName='language')
    # POFile.variant
    variant = StringCol(dbName='variant')
    # POFile.topcomment
    potopcomment = StringCol(dbName='potopcomment')
    # POFile.header
    poheader = StringCol(dbName='poheader')
    # POFile.fuzzyheader
    pofuzzyheader = BoolCol(dbName='pofuzzyheader')
    # POFile.pluralforms
    popluralforms = IntCol(dbName='popluralforms')

    # POTMsgSet.id
    potmsgset = IntCol(dbName='potmsgset')
    # POTMsgSet.sequence
    potsequence = IntCol(dbName='potsequence')
    # POTMsgSet.commenttext
    potcommenttext = StringCol(dbName='potcommenttext')
    # POTMsgSet.sourcecomment
    sourcecomment = StringCol(dbName='sourcecomment')
    # POTMsgSet.flagscomment
    flagscomment = StringCol(dbName='flagscomment')
    # POTMsgSet.filereferences
    filereferences = StringCol(dbName='filereferences')

    # POMsgSet.id
    pomsgset = IntCol(dbName='pomsgset')
    # POMsgSet.sequence
    posequence = IntCol(dbName='posequence')
    # POMsgSet.iscomplete
    iscomplete = BoolCol(dbName='iscomplete')
    # POMsgSet.obsolete
    obsolete = BoolCol(dbName='obsolete')
    # POMsgSet.fuzzy
    fuzzy = BoolCol(dbName='fuzzy')
    # POMsgSet.commenttext
    pocommenttext = StringCol(dbName='pocommenttext')

    # POMsgIDSighting.pluralform
    msgidpluralform = IntCol(dbName='msgidpluralform')

    # POTranslationSighting.pluralform
    translationpluralform = IntCol(dbName='translationpluralform')
    # POTranslationSighting.active
    active = BoolCol(dbName='active')

    # POMsgID.pomsgid
    msgid = StringCol(dbName='msgid')

    # POTranslation.translation
    translation = StringCol(dbName='translation')

