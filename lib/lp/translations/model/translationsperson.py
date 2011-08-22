# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'TranslationsPerson',
    ]

from storm.expr import (
    And,
    Coalesce,
    Desc,
    Join,
    LeftJoin,
    Or,
    )
from storm.info import ClassAlias
from storm.store import Store
from zope.component import (
    adapts,
    getUtility,
    )
from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from lp.app.enums import ServiceUsage
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.person import IPerson
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.product import Product
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.projectgroup import ProjectGroup
from lp.registry.model.teammembership import TeamParticipation
from lp.services.worlddata.model.language import Language
from lp.translations.enums import TranslationPermission
from lp.translations.interfaces.translationgroup import ITranslationGroupSet
from lp.translations.interfaces.translationsperson import ITranslationsPerson
from lp.translations.interfaces.translator import ITranslatorSet
from lp.translations.model.pofile import POFile
from lp.translations.model.pofiletranslator import POFileTranslator
from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationgroup import TranslationGroup
from lp.translations.model.translationrelicensingagreement import (
    TranslationRelicensingAgreement,
    )
from lp.translations.model.translator import Translator


class TranslationsPerson:
    """See `ITranslationsPerson`."""
    implements(ITranslationsPerson)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person

    @property
    def translatable_languages(self):
        """See `ITranslationsPerson`."""
        return Language.select("""
            Language.id = PersonLanguage.language AND
            PersonLanguage.person = %s AND
            Language.code <> 'en' AND
            Language.visible""" % sqlvalues(self.person),
            clauseTables=['PersonLanguage'], orderBy='englishname')

    def getTranslationHistory(self, no_older_than=None):
        """See `ITranslationsPerson`."""
        conditions = (POFileTranslator.person == self.person)
        if no_older_than is not None:
            conditions = And(
                conditions,
                POFileTranslator.date_last_touched >= no_older_than)

        entries = Store.of(self.person).find(POFileTranslator, conditions)
        return entries.order_by(Desc(POFileTranslator.date_last_touched))

    def hasTranslated(self):
        """See `ITranslationsPerson`."""
        return self.getTranslationHistory().any() is not None

    @property
    def translation_history(self):
        """See `ITranslationsPerson`."""
        return self.getTranslationHistory()

    @property
    def translation_groups(self):
        """See `ITranslationsPerson`."""
        return getUtility(ITranslationGroupSet).getByPerson(self.person)

    @property
    def translators(self):
        """See `ITranslationsPerson`."""
        return getUtility(ITranslatorSet).getByTranslator(self.person)

    def get_translations_relicensing_agreement(self):
        """Return whether translator agrees to relicense their translations.

        If she has made no explicit decision yet, return None.
        """
        relicensing_agreement = TranslationRelicensingAgreement.selectOneBy(
            person=self.person)
        if relicensing_agreement is None:
            return None
        else:
            return relicensing_agreement.allow_relicensing

    def set_translations_relicensing_agreement(self, value):
        """Set a translations relicensing decision by translator.

        If she has already made a decision, overrides it with the new one.
        """
        relicensing_agreement = TranslationRelicensingAgreement.selectOneBy(
            person=self.person)
        if relicensing_agreement is None:
            relicensing_agreement = TranslationRelicensingAgreement(
                person=self.person,
                allow_relicensing=value)
        else:
            relicensing_agreement.allow_relicensing = value

    translations_relicensing_agreement = property(
        get_translations_relicensing_agreement,
        set_translations_relicensing_agreement,
        doc="See `ITranslationsPerson`.")

    def getReviewableTranslationFiles(self, no_older_than=None):
        """See `ITranslationsPerson`."""
        if self.person.isTeam():
            # A team as such does not work on translations.  Skip the
            # search for ones the team has worked on.
            return []

        tables = self._composePOFileReviewerJoins()

        # Consider only translations that this person is a reviewer for.
        translator_join, translator_condition = (
            self._composePOFileTranslatorJoin(True, no_older_than))
        tables.append(translator_join)

        conditions = And(
            POFile.unreviewed_count > 0, translator_condition)

        source = Store.of(self.person).using(*tables)
        query = source.find(POFile, conditions)
        return query.config(distinct=True).order_by(POFile.date_changed)

    def suggestReviewableTranslationFiles(self, no_older_than=None):
        """See `ITranslationsPerson`."""
        tables = self._composePOFileReviewerJoins()

        # Pick files that this person has no recent POFileTranslator entry
        # for.
        translator_join, translator_condition = (
            self._composePOFileTranslatorJoin(False, no_older_than))
        tables.append(translator_join)

        conditions = And(POFile.unreviewed_count > 0, translator_condition)

        source = Store.of(self.person).using(*tables)
        query = source.find(POFile, conditions)
        return query.config(distinct=True).order_by(POFile.id)

    def _queryTranslatableFiles(self, worked_on, no_older_than=None,
                                languages=None):
        """Get `POFile`s this person could help translate.

        :param worked_on: If True, get `POFile`s that the person has
            been working on recently (where "recently" is defined as
            `no_older_than`).  If False, get ones that the person has
            not been working on recently (those that the person has
            never worked on, or last worked on before `no_older_than`).
        :param no_older_than: Oldest involvement to consider.  If the
            person last worked on a `POFile` before this date, that
            counts as not having worked on it.
        :param languages: Optional set of languages to restrict search to.
        :return: An unsorted query yielding `POFile`s.
        """
        if self.person.isTeam():
            return []

        tables = self._composePOFileReviewerJoins(
            expect_reviewer_status=False)

        translator_join, translator_condition = (
            self._composePOFileTranslatorJoin(worked_on, no_older_than))
        tables.append(translator_join)

        translated_count = (
            POFile.currentcount + POFile.updatescount + POFile.rosettacount)

        conditions = And(
            translated_count < POTemplate.messagecount, translator_condition)

        # The person must not be a reviewer for this translation (unless
        # it's in the sense that any user gets review permissions
        # for it).
        permission = Coalesce(
            Distribution.translationpermission,
            Product.translationpermission,
            ProjectGroup.translationpermission)
        Reviewership = ClassAlias(TeamParticipation, 'Reviewership')
        # XXX JeroenVermeulen 2009-08-28 bug=420364: Storm's Coalesce()
        # can't currently infer its return type from its inputs, leading
        # to a "can't adapt" error.  Using the enum's .value works
        # around the problem.
        not_reviewer = Or(
            permission == TranslationPermission.OPEN.value,
            And(
                permission == TranslationPermission.STRUCTURED.value,
                Translator.id == None),
            And(
                permission == TranslationPermission.RESTRICTED.value,
                Translator.id != None,
                Reviewership.id == None))

        conditions = And(conditions, not_reviewer)

        if languages is not None:
            conditions = And(conditions, POFile.languageID.is_in(languages))

        source = Store.of(self.person).using(*tables)
        return source.find(POFile, conditions)

    def getTranslatableFiles(self, no_older_than=None, urgent_first=True):
        """See `ITranslationsPerson`."""
        results = self._queryTranslatableFiles(True, no_older_than)

        translated_count = (
            POFile.currentcount + POFile.updatescount + POFile.rosettacount)
        ordering = translated_count - POTemplate.messagecount
        if not urgent_first:
            ordering = -ordering

        return results.order_by(ordering)

    def suggestTranslatableFiles(self, no_older_than=None):
        """See `ITranslationsPerson`."""
        # XXX JeroenVermeulen 2009-08-28: Ideally this would also check
        # for a free license.  That's hard to do in SQL though.
        languages = set([
            language.id for language in self.translatable_languages])
        results = self._queryTranslatableFiles(
            False, no_older_than, languages=languages)
        return results.order_by(['random()'])

    def _composePOFileReviewerJoins(self, expect_reviewer_status=True):
        """Compose certain Storm joins for common `POFile` queries.

        Returns a list of Storm joins for a query on `POFile`.  The
        joins will involve `Distribution`, `DistroSeries`, `POFile`,
        `Product`, `ProductSeries`, `ProjectGroup`, `TranslationGroup`,
        `TranslationTeam`, and `Translator`.

        The joins will restrict the ultimate query to `POFile`s
        distributions that use Launchpad for translations, which have a
        translation group and for which `self` is a reviewer.

        The added joins may make the overall query non-distinct, so be
        sure to enforce distinctness.
        """

        POTemplateJoin = Join(POTemplate, And(
            POTemplate.id == POFile.potemplateID,
            POTemplate.iscurrent == True))

        # This is a weird and complex diamond join.  Both DistroSeries
        # and ProductSeries are left joins, but one of them may
        # ultimately lead to a TranslationGroup.  In the case of
        # ProductSeries it may lead to up to two: one for the Product
        # and one for the ProjectGroup.
        DistroSeriesJoin = LeftJoin(
            DistroSeries, DistroSeries.id == POTemplate.distroseriesID)

        # If there's a DistroSeries, it should be the distro's
        # translation focus.
        distrojoin_conditions = And(
            Distribution.id == DistroSeries.distributionID,
            Distribution._translations_usage == ServiceUsage.LAUNCHPAD,
            Distribution.translation_focusID == DistroSeries.id)

        DistroJoin = LeftJoin(Distribution, distrojoin_conditions)

        ProductSeriesJoin = LeftJoin(
            ProductSeries, ProductSeries.id == POTemplate.productseriesID)
        # XXX j.c.sackett 2010-11-19 bug=677532 It's less than ideal that
        # this query is using _translations_usage, but there's no cleaner
        # way to deal with it. Once the bug above is resolved, this should
        # should be fixed to use translations_usage.
        ProductJoin = LeftJoin(Product, And(
            Product.id == ProductSeries.productID,
            Product._translations_usage == ServiceUsage.LAUNCHPAD,
            Product.active == True))

        ProjectJoin = LeftJoin(
            ProjectGroup, ProjectGroup.id == Product.projectID)

        # Look up translation group.
        groupjoin_conditions = Or(
            TranslationGroup.id == Product.translationgroupID,
            TranslationGroup.id == Distribution.translationgroupID,
            TranslationGroup.id == ProjectGroup.translationgroupID)
        if expect_reviewer_status:
            GroupJoin = Join(TranslationGroup, groupjoin_conditions)
        else:
            GroupJoin = LeftJoin(TranslationGroup, groupjoin_conditions)

        # Look up translation team.
        translatorjoin_conditions = And(
            Translator.translationgroupID == TranslationGroup.id,
            Translator.languageID == POFile.languageID)
        if expect_reviewer_status:
            TranslatorJoin = Join(Translator, translatorjoin_conditions)
        else:
            TranslatorJoin = LeftJoin(Translator, translatorjoin_conditions)

        # Check for translation-team membership.  Use alias for
        # TeamParticipation; the query may want to include other
        # instances of that table.  It's just a linking table so the
        # query won't be interested in its actual contents anyway.
        Reviewership = ClassAlias(TeamParticipation, 'Reviewership')
        reviewerjoin_condition = And(
            Reviewership.teamID == Translator.translatorID,
            Reviewership.personID == self.person.id)
        if expect_reviewer_status:
            TranslationTeamJoin = Join(Reviewership, reviewerjoin_condition)
        else:
            TranslationTeamJoin = LeftJoin(
                Reviewership, reviewerjoin_condition)

        return [
            POFile,
            POTemplateJoin,
            DistroSeriesJoin,
            DistroJoin,
            ProductSeriesJoin,
            ProductJoin,
            ProjectJoin,
            GroupJoin,
            TranslatorJoin,
            TranslationTeamJoin,
            ]

    def _composePOFileTranslatorJoin(self, expected_presence,
                                     no_older_than=None):
        """Compose join condition for `POFileTranslator`.

        Checks for a `POFileTranslator` record matching a `POFile` and
        `Person` in a join.

        :param expected_presence: whether the `POFileTranslator` record
            is to be present, or absent.  The join will enforce presence
            through a regular inner join, or absence by an outer join
            with a condition that the record not be present.
        :param no_older_than: optional cutoff date.  `POFileTranslator`
            records older than this date are not considered.
        :return: a tuple of the join, and a condition to be checked by
            the query.  Combine it with the query's other conditions
            using `And`.
        """
        join_condition = And(
            POFileTranslator.personID == self.person.id,
            POFileTranslator.pofileID == POFile.id,
            POFile.language != getUtility(ILaunchpadCelebrities).english)

        if no_older_than is not None:
            join_condition = And(
                join_condition,
                POFileTranslator.date_last_touched >= no_older_than)

        if expected_presence:
            # A regular inner join enforces this.  No need for an extra
            # condition; the join does it more efficiently.
            return Join(POFileTranslator, join_condition), True
        else:
            # Check for absence.  Usually the best way to check for this
            # is an outer join plus a condition that the outer join
            # match no record.
            return (
                LeftJoin(POFileTranslator, join_condition),
                POFileTranslator.id == None)
