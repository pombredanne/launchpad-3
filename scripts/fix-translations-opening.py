#!/usr/bin/python -S

__metaclass__ = type

import _pythonpath

from zope.component import getUtility
from zope.interface import implements

from lp.services.looptuner import (
    DBLoopTuner,
    ITunableLoop,
    )
from lp.services.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from lp.services.scripts.base import LaunchpadScript


series_name = 'quantal'

select_series = """\
SELECT DistroSeries.id
  FROM DistroSeries
  JOIN Distribution ON
           Distribution.id = DistroSeries.distribution
 WHERE Distribution.name = 'ubuntu'
   AND DistroSeries.name = '%s'
""" % series_name

delete_pofiletranslator = """\
DELETE FROM POFileTranslator
 WHERE POFileTranslator.id IN (
    SELECT POFileTranslator.id
      FROM POFileTranslator, POFile, POTemplate
     WHERE POFileTranslator.pofile = POFile.id
       AND POFile.potemplate = POTemplate.id
       AND POTemplate.distroseries = (%s)
     LIMIT ?)
""" % select_series

null_translationimportqueueentry_pofile = """\
UPDATE TranslationImportQueueEntry
   SET pofile = NULL
 WHERE TranslationImportQueueEntry.id IN (
    SELECT TranslationImportQueueEntry.id
      FROM TranslationImportQueueEntry, POFile, POTemplate
     WHERE TranslationImportQueueEntry.pofile = POFile.id
       AND POFile.potemplate = POTemplate.id
       AND POTemplate.distroseries = (%s)
     LIMIT ?)
""" % select_series

delete_pofile = """\
DELETE FROM POFile
 WHERE POFile.id IN (
    SELECT POFile.id
      FROM POFile, POTemplate
     WHERE POFile.potemplate = POTemplate.id
       AND POTemplate.distroseries = (%s)
     LIMIT ?)
""" % select_series

delete_translationtemplateitem = """\
DELETE FROM TranslationTemplateItem
 WHERE TranslationTemplateItem.id IN (
    SELECT TranslationTemplateItem.id
      FROM TranslationTemplateItem, POTemplate
     WHERE TranslationTemplateItem.potemplate = POTemplate.id
       AND POTemplate.distroseries = (%s)
     LIMIT ?)
""" % select_series

delete_packagingjob = """\
DELETE FROM PackagingJob
 WHERE PackagingJob.id IN (
    SELECT PackagingJob.id
      FROM PackagingJob, POTemplate
     WHERE PackagingJob.potemplate = POTemplate.id
       AND POTemplate.distroseries = (%s)
     LIMIT ?)
""" % select_series

null_translationimportqueueentry_potemplate = """\
UPDATE TranslationImportQueueEntry
   SET potemplate = NULL
 WHERE TranslationImportQueueEntry.id IN (
    SELECT TranslationImportQueueEntry.id
      FROM TranslationImportQueueEntry, POTemplate
     WHERE TranslationImportQueueEntry.potemplate = POTemplate.id
       AND POTemplate.distroseries = (%s)
     LIMIT ?)
""" % select_series

delete_potemplate = """\
DELETE FROM POTemplate
 WHERE POTemplate.id IN (
    SELECT POTemplate.id
      FROM POTemplate
     WHERE POTemplate.distroseries = (%s)
     LIMIT ?)
""" % select_series

statements = [
    delete_pofiletranslator,
    null_translationimportqueueentry_pofile,
    delete_pofile,
    delete_translationtemplateitem,
    delete_packagingjob,
    null_translationimportqueueentry_potemplate,
    delete_potemplate,
    ]


class ExecuteLoop:

    implements(ITunableLoop)

    def __init__(self, statement, logger):
        self.statement = statement
        self.logger = logger
        self.done = False

    def isDone(self):
        return self.done

    def __call__(self, chunk_size):
        self.logger.info(
            "%s (limited to %d rows)",
            self.statement.splitlines()[0],
            chunk_size)
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        result = store.execute(self.statement, (chunk_size,))
        self.done = (result.rowcount == 0)
        self.logger.info(
            "%d rows deleted (%s)", result.rowcount,
            ("done" if self.done else "not done"))
        store.commit()


class WipeSeriesTranslationsScript(LaunchpadScript):

    description = "Wipe Ubuntu %s's translations." % series_name.title()

    def add_my_options(self):
        self.parser.epilog = (
            "Before running this script you must `GRANT DELETE ON TABLE "
            "PackagingJob TO rosettaadmin` and afterwards you ought to "
            "`REVOKE DELETE ON PackagingJob FROM rosettaadmin`.")

    def main(self):
        for statement in statements:
            delete = ExecuteLoop(statement, self.logger)
            tuner = DBLoopTuner(delete, 2.0, maximum_chunk_size=5000)
            tuner.run()


if __name__ == '__main__':
    WipeSeriesTranslationsScript(dbuser='rosettaadmin').run()
