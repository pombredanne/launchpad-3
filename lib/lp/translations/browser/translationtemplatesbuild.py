# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Display `TranslationTemplateBuild`s."""

__metaclass__ = type
__all__ = [
    'TranslationTemplatesBuildNavigation',
    'TranslationTemplatesBuildUrl',
    'TranslationTemplatesBuildView',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.tales import DateTimeFormatterAPI
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.productseries import IProductSeriesSet
from lp.services.propertycache import cachedproperty


class TranslationTemplatesBuildView(LaunchpadView):

    def getTargets(self):
        utility = getUtility(IProductSeriesSet)
        return utility.findByTranslationsImportBranch(self.context.branch)

    @property
    def status(self):
        return self.context.status

    def isBuilding(self):
        return self.status == BuildStatus.BUILDING

    @cachedproperty
    def current_builder(self):
        if self.isBuilding():
            return self.context.buildqueue.builder
        else:
            return self.context.builder

    def getDispatchTime(self):
        if self.context.was_built:
            return self.context.buildqueue_record.job.date_started
        elif self.context.date_started is not None:
            return self.context.date_started
        elif self.context.buildqueue_record is not None:
            return self.context.buildqueue_record.getEstimatedJobStartTime()
        else:
            return None

    def _composeTimeText(self, time, preamble=''):
        if time is None:
            return None
        formatter = DateTimeFormatterAPI(time)
        return '%s <span title="%s">%s</span>' % (
            preamble, formatter.datetime(), formatter.approximatedate())

    def composeDispatchTimeText(self):
        if self.context.date_started is None:
            preamble = "Start"
        else:
            preamble = "Started"

        return self._composeTimeText(self.getDispatchTime(), preamble)

    def composeFinishTimeText(self):
        return self._composeTimeText(self.context.date_finished, "Finished")

    @cachedproperty
    def last_score(self):
        return self.context.buildqueue.lastscore
