# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database class to handle translation export view."""

__metaclass__ = type

__all__ = [
    'VPOExportSet',
    'VPOExport'
    ]

from zope.component import getUtility
from zope.interface import implements

from storm.expr import And, Or
from storm.store import Store

from canonical.database.sqlbase import quote, sqlvalues
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)
from lp.soyuz.model.component import Component
from lp.soyuz.model.publishing import (
    SourcePackagePublishingHistory)
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.interfaces.translations import TranslationConstants
from lp.soyuz.model.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.interfaces import IVPOExportSet, IVPOExport


class VPOExportSet:
    """Retrieve collections of `VPOExport` objects."""

    implements(IVPOExportSet)

    # Names of columns that are selected and passed (in this order) to
    # the VPOExport constructor.
    column_names = [
        'POTMsgSet.id',
        'TranslationTemplateItem.sequence',
        'TranslationMessage.comment',
        'msgid_singular.msgid',
        'msgid_plural.msgid',
        'TranslationMessage.is_current',
        'TranslationMessage.is_imported',
        'TranslationMessage.potemplate',
        'potranslation0.translation',
        'potranslation1.translation',
        'potranslation2.translation',
        'potranslation3.translation',
        'potranslation4.translation',
        'potranslation5.translation',
    ]
    columns = ', '.join(column_names)

    # Obsolete translations are marked with a sequence number of 0, so they
    # would get sorted to the front of the file during export. To avoid that,
    # sequence numbers of 0 are translated to NULL and ordered to the end
    # with NULLS LAST so that they appear at the end of the file.
    sort_column_names = [
        'TranslationMessage.potemplate NULLS LAST',
        'CASE '
            'WHEN TranslationTemplateItem.sequence = 0 THEN NULL '
            'ELSE TranslationTemplateItem.sequence '
        'END NULLS LAST',
        'TranslationMessage.id',
    ]
    sort_columns = ', '.join(sort_column_names)

    def _select(self, pofile, where=None, ignore_obsolete=True):
        """Select translation message data.

        Diverged messages come before shared ones.  The exporter relies
        on this.
        """

        # Prefetch all POTMsgSets for this template in one go.
        potmsgsets = {}
        for potmsgset in pofile.potemplate.getPOTMsgSets(ignore_obsolete):
            potmsgsets[potmsgset.id] = potmsgset

        main_select = "SELECT %s" % self.columns
        query = main_select + """
            FROM POTMsgSet
            JOIN TranslationTemplateItem ON
                TranslationTemplateItem.potemplate = %s AND
                TranslationTemplateItem.potmsgset = POTMsgSet.id
            LEFT JOIN TranslationMessage ON (
                TranslationMessage.potmsgset =
                    TranslationTemplateItem.potmsgset AND
                TranslationMessage.is_current IS TRUE AND
                TranslationMessage.language = %s
                )
            LEFT JOIN POMsgID AS msgid_singular ON
                msgid_singular.id = POTMsgSet.msgid_singular
            LEFT JOIN POMsgID msgid_plural ON
                msgid_plural.id = POTMsgSet.msgid_plural
            """ % sqlvalues(pofile.potemplate, pofile.language)

        for form in xrange(TranslationConstants.MAX_PLURAL_FORMS):
            alias = "potranslation%d" % form
            field = "TranslationMessage.msgstr%d" % form
            query += "LEFT JOIN POTranslation AS %s ON %s.id = %s\n" % (
                    alias, alias, field)

        conditions = [
            "(TranslationMessage.potemplate IS NULL OR "
                 "TranslationMessage.potemplate = %s)" % quote(
                    pofile.potemplate),
            ]

        if pofile.variant:
            conditions.append("TranslationMessage.variant = %s" % quote(
                pofile.variant))
        else:
            conditions.append("TranslationMessage.variant IS NULL")

        if ignore_obsolete:
            conditions.append("TranslationTemplateItem.sequence <> 0")

        if where:
            conditions.append("(%s)" % where)

        query += "WHERE %s" % ' AND '.join(conditions)
        query += ' ORDER BY %s' % self.sort_columns

        for row in Store.of(pofile).execute(query):
            export_data = VPOExport(*row)
            export_data.setRefs(pofile, potmsgsets)
            yield export_data

    def get_pofile_rows(self, pofile):
        """See `IVPOExportSet`."""
        # Only fetch rows that belong to this POFile and are "interesting":
        # they must either be in the current template (sequence != 0, so not
        # "obsolete") or be in the current imported version of the translation
        # (is_imported), or both.
        return self._select(
            pofile, ignore_obsolete=False,
            where="TranslationTemplateItem.sequence <> 0 OR "
                "is_imported IS TRUE")

    def get_pofile_changed_rows(self, pofile):
        """See `IVPOExportSet`."""
        return self._select(pofile, where="is_imported IS FALSE")

    def get_distroseries_pofiles(self, series, date=None, component=None,
                                 languagepack=None):
        """See `IVPOExport`.

        Selects `POFiles` based on the 'series', last modified 'date',
        archive 'component', and whether it belongs to a 'languagepack'
        """
        tables = [
            POFile,
            POTemplate,
            ]

        conditions = [
            POTemplate.distroseries == series,
            POTemplate.iscurrent == True,
            POFile.potemplate == POTemplate.id,
            ]

        if date is not None:
            conditions.append(Or(
                POTemplate.date_last_updated > date,
                POFile.date_changed > date))

        if component is not None:
            tables.extend([
                SourcePackagePublishingHistory,
                SourcePackageRelease,
                Component,
                ])
            conditions.extend([
                SourcePackagePublishingHistory.distroseries == series,
                SourcePackagePublishingHistory.sourcepackagerelease ==
                     SourcePackageRelease.id,
                SourcePackagePublishingHistory.component == Component.id,
                POTemplate.sourcepackagename ==
                    SourcePackageRelease.sourcepackagenameID,
                Component.name == component,
                SourcePackagePublishingHistory.dateremoved == None,
                SourcePackagePublishingHistory.archive == series.main_archive,
                ])

        if languagepack:
            conditions.append(POTemplate.languagepack == True)

        # Use the slave store.  We may want to write to the distroseries
        # to register a language pack, but not to the translation data
        # we retrieve for it.
        store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        query = store.using(*tables).find(POFile, And(*conditions))

        # Order by POTemplate.  Caching in the export scripts can be
        # much more effective when consecutive POFiles belong to the
        # same POTemplate, e.g. they'll have the same POTMsgSets.
        sort_list = [POFile.potemplateID, POFile.languageID, POFile.variant]
        return query.order_by(sort_list).config(distinct=True)

    def get_distroseries_pofiles_count(self, series, date=None,
                                        component=None, languagepack=None):
        """See `IVPOExport`."""
        return self.get_distroseries_pofiles(
            series, date, component, languagepack).count()


class VPOExport:
    """Present translations in a form suitable for efficient export."""
    implements(IVPOExport)

    productseries = None
    sourcepackagename = None
    distroseries = None
    potemplate = None
    template_header = None
    languagepack = None
    pofile = None
    language = None
    variant = None
    translation_file_comment = None
    translation_header = None
    is_translation_header_fuzzy = None

    potmsgset_id = None
    potmsgset = None
    source_comment = None
    file_references = None
    flags_comment = None
    context = None

    def __init__(self, *args):
        """Store raw data as given in `VPOExport.column_names`."""
        (self.potmsgset_id,
         self.sequence,
         self.comment,
         self.msgid_singular,
         self.msgid_plural,
         self.is_current,
         self.is_imported,
         self.diverged,
         self.translation0,
         self.translation1,
         self.translation2,
         self.translation3,
         self.translation4,
         self.translation5) = args

    def setRefs(self, pofile, potmsgsets_lookup):
        """Store various object references.

        :param pofile: the `POFile` that this export is for.
        :param potmsgsets_lookup: a dict mapping numeric ids to `POTMsgSet`s.
            This saves the ORM the job of fetching them one by one as other
            objects refer to them.
        """
        template = pofile.potemplate
        if template.productseries is not None:
            self.productseries = template.productseries.id
        else:
            self.sourcepackagename = template.sourcepackagename.id
            self.distroseries = template.distroseries.id

        self.potemplate = template
        self.template_header = template.header

        self.pofile = pofile
        self.language = pofile.language
        self.variant = pofile.variant

        potmsgset = potmsgsets_lookup[self.potmsgset_id]
        self.potmsgset = potmsgset
        self.source_comment = potmsgset.sourcecomment
        self.file_references = potmsgset.filereferences
        self.flags_comment = potmsgset.flagscomment
        self.context = potmsgset.context

        if potmsgset.is_translation_credit:
            self.translation0 = pofile.prepareTranslationCredits(potmsgset)
