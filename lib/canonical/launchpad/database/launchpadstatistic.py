# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Classes that implement LaunchpadStatistics."""

__metaclass__ = type

__all__ = [
    'LaunchpadStatistic',
    'LaunchpadStatisticSet',
    ]

from zope.interface import implements
from zope.component import getUtility

from sqlobject import IntCol, StringCol
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.database.sqlbase import SQLBase, cursor, sqlvalues
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.bugtask import BugTask
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.question import Question

from canonical.launchpad.interfaces import (
    ILaunchpadStatistic, ILaunchpadStatisticSet, IPersonSet, QuestionStatus
    )


class LaunchpadStatistic(SQLBase):
    """A table of Launchpad Statistics."""

    implements(ILaunchpadStatistic)

    _table = 'LaunchpadStatistic'
    _defaultOrder = 'name'

    # db field names
    name = StringCol(notNull=True, alternateID=True, unique=True)
    value = IntCol(notNull=True)
    dateupdated = UtcDateTimeCol(notNull=True, default=UTC_NOW)


class LaunchpadStatisticSet:
    """See canonical.launchpad.interfaces.ILaunchpadStatisticSet."""

    implements(ILaunchpadStatisticSet)

    def __iter__(self):
        """See ILaunchpadStatisticSet."""
        return iter(LaunchpadStatistic.select(orderBy='name'))

    def update(self, name, value):
        """See ILaunchpadStatisticSet."""
        stat = LaunchpadStatistic.selectOneBy(name=name)
        if stat is None:
            stat = LaunchpadStatistic(name=name, value=value)
        else:
            stat.value = value
            stat.dateupdated = UTC_NOW

    def dateupdated(self, name):
        """See ILaunchpadStatisticSet."""
        stat = LaunchpadStatistic.selectOneBy(name=name)
        if stat is None:
            return None
        return stat.dateupdated

    def value(self, name):
        """See ILaunchpadStatisticSet."""
        stat = LaunchpadStatistic.selectOneBy(name=name)
        if stat is None:
            return None
        return stat.value

    def updateStatistics(self, ztm):
        """See ILaunchpadStatisticSet."""
        self._updateMaloneStatistics(ztm)
        self._updateRegistryStatistics(ztm)
        self._updateRosettaStatistics(ztm)
        self._updateQuestionStatistics(ztm)
        getUtility(IPersonSet).updateStatistics(ztm)

    def _updateMaloneStatistics(self, ztm):
        self.update('bug_count', Bug.select().count())
        ztm.commit()

        self.update('bugtask_count', BugTask.select().count())
        ztm.commit()

        self.update(
                'products_using_malone',
                Product.selectBy(official_malone=True).count()
                )
        ztm.commit()

        cur = cursor()
        cur.execute(
            "SELECT COUNT(DISTINCT product) + COUNT(DISTINCT distribution) "
            "FROM BugTask")
        self.update("projects_with_bugs", cur.fetchone()[0] or 0)
        ztm.commit()

        cur = cursor()
        cur.execute(
            "SELECT COUNT(*) FROM (SELECT COUNT(distinct product) + "
            "                             COUNT(distinct distribution) "
            "                             AS places "
            "                             FROM BugTask GROUP BY bug) "
            "                      AS temp WHERE places > 1")
        self.update("shared_bug_count", cur.fetchone()[0] or 0)
        ztm.commit()

    def _updateRegistryStatistics(self, ztm):
        self.update(
            'active_products',
            Product.select("active IS TRUE", distinct=True).count())
        self.update(
            'products_with_translations',
            Product.select('''
                POTemplate.productseries = ProductSeries.id AND
                Product.id = ProductSeries.product AND
                Product.active = TRUE
                ''',
                clauseTables=['ProductSeries', 'POTemplate'],
                distinct=True).count())
        self.update(
            'products_with_blueprints',
            Product.select(
                "Specification.product=Product.id AND Product.active IS TRUE",
                distinct=True, clauseTables=['Specification']).count())
        self.update(
            'products_with_branches',
            Product.select(
                "Branch.product=Product.id AND Product.active IS TRUE",
                distinct=True, clauseTables=['Branch']).count())
        self.update(
            'products_with_bugs',
            Product.select(
                "BugTask.product=Product.id AND Product.active IS TRUE",
                distinct=True, clauseTables=['BugTask']).count())
        self.update(
            'products_with_questions',
            Product.select(
                "Question.product=Product.id AND Product.active IS TRUE",
                distinct=True, clauseTables=['Question']).count())
        self.update(
            'reviewed_products',
            Product.selectBy(reviewed=True, active=True).count())

    def _updateRosettaStatistics(self, ztm):
        self.update(
                'products_using_rosetta',
                Product.selectBy(official_rosetta=True).count()
                )
        self.update('potemplate_count', POTemplate.select().count())
        ztm.commit()
        self.update('pofile_count', POFile.select().count())
        ztm.commit()
        self.update('pomsgid_count', POMsgID.select().count())
        ztm.commit()
        self.update('language_count', Language.select(
            "POFile.language=Language.id",
            clauseTables=['POFile'],
            distinct=True).count())
        ztm.commit()

        cur = cursor()
        cur.execute(
            "SELECT COUNT(DISTINCT submitter) FROM TranslationMessage")
        self.update('translator_count', cur.fetchone()[0] or 0)
        ztm.commit()

        cur = cursor()
        cur.execute("""
            SELECT COUNT(DISTINCT submitter)
            FROM TranslationMessage
            WHERE origin=2
            """)
        self.update('rosetta_translator_count', cur.fetchone()[0] or 0)
        ztm.commit()

        cur = cursor()
        cur.execute("""
            SELECT COUNT(DISTINCT product) FROM ProductSeries,POTemplate
            WHERE ProductSeries.id = POTemplate.productseries
            """)
        self.update('products_with_potemplates', cur.fetchone()[0] or 0)
        ztm.commit()

    def _updateQuestionStatistics(self, ztm):
        self.update('question_count', Question.select().count())
        ztm.commit()

        self.update(
            'answered_question_count',
            Question.select(
              'status = %s' % sqlvalues(QuestionStatus.ANSWERED)).count())
        ztm.commit()

        self.update(
            'solved_question_count',
            Question.select(
              'status = %s' % sqlvalues(QuestionStatus.SOLVED)).count())
        ztm.commit()

        cur = cursor()
        cur.execute(
            "SELECT COUNT(DISTINCT product) + COUNT(DISTINCT distribution) "
            "FROM Question")
        self.update("projects_with_questions_count", cur.fetchone()[0] or 0)
        ztm.commit()

