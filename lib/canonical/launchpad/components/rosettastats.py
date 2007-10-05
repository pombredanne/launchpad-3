from zope.interface import implements

from canonical.launchpad.interfaces import IRosettaStats

# XXX: Carlos Perello Marin 2005-04-14 bug=396:
# This code should be change to be an adaptor.

class RosettaStats(object):

    implements(IRosettaStats)

    def testStatistics(self):
        """See IRosettaStats."""
        if self.nonUpdatesCount()+self.updatesCount() != self.currentCount():
            return False
        if self.untranslatedCount() < 0:
            return False
        if self.untranslatedCount() > self.messageCount():
            return False
        if self.translatedCount() > self.messageCount():
            return False
        return True

    def updateStatistics(self):
        """See IRosettaStats."""
        # this method should be overridden by the objects that inherit from
        # this class
        pass

    def messageCount(self):
        """See IRosettaStats."""
        # This method should be overrided by the objects that inherit from
        # this class
        return 0

    def currentCount(self, language=None):
        """See IRosettaStats."""
        # This method should be overrided by the objects that inherit from
        # this class
        return 0

    def updatesCount(self, language=None):
        """See IRosettaStats."""
        # This method should be overrided by the objects that inherit from
        # this class
        return 0

    def rosettaCount(self, language=None):
        """See IRosettaStats."""
        # This method should be overrided by the objects that inherit from
        # this class
        return 0

    def translatedCount(self, language=None):
        """See IRosettaStats."""
        return self.currentCount(language) + self.rosettaCount(language)

    def untranslatedCount(self, language=None):
        """See IRosettaStats."""
        untranslated = self.messageCount() - self.translatedCount(language)
        # Statistics should not be ever less than 0
        assert (untranslated >= 0,
            'Stats error in %r id %d, %d untranslated' % (
                self, self.id, untranslated))
        return untranslated

    def nonUpdatesCount(self, language=None):
        """See IRosettaStats."""
        nonupdates = self.currentCount() - self.updatesCount()
        if nonupdates < 0:
            return 0
        else:
            return nonupdates

    def asPercentage(self, value):
        """See IRosettaStats."""
        if self.messageCount() > 0:
            percent = float(value) / self.messageCount()
            percent *= 100
            percent = round(percent, 2)
        else:
            percent = 0
        # We use float(str()) to prevent problems with some floating point
        # representations that could give us:
        # >>> x = 3.141592
        # >>> round(x, 2)
        # 3.1400000000000001
        # >>>
        return float(str(percent))

    def translatedPercentage(self, language=None):
        """See IRosettaStats."""
        return self.asPercentage(self.translatedCount(language))

    def currentPercentage(self, language=None):
        """See IRosettaStats."""
        return self.asPercentage(self.currentCount(language))

    def untranslatedPercentage(self, language=None):
        """See IRosettaStats."""
        return self.asPercentage(self.untranslatedCount(language))

    def nonUpdatesPercentage(self, language=None):
        """See IRosettaStats."""
        return self.asPercentage(self.nonUpdatesCount(language))

    def updatesPercentage(self, language=None):
        """See IRosettaStats."""
        return self.asPercentage(self.updatesCount(language))

    def rosettaPercentage(self, language=None):
        """See IRosettaStats."""
        return self.asPercentage(self.rosettaCount(language))

