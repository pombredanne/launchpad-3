from zope.interface import implements

from canonical.launchpad.interfaces import IRosettaStats

# XXX: Carlos Perello Marin 2005-04-14 This code should be change to be an
# adaptor as bug #396 describes.

class RosettaStats(object):
    implements(IRosettaStats)

    def messageCount(self):
        # This method should be overrided by the objects that inherit from
        # this object.
        return 0

    def currentCount(self, language=None):
        # This method should be overrided by the objects that inherit from
        # this object.
        return 0

    def currentPercentage(self, language=None):
        if self.messageCount() > 0:
            percent = float(self.currentCount(language)) / self.messageCount()
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

    def updatesCount(self, language=None):
        # This method should be overrided by the objects that inherit from
        # this object.
        return 0

    def updatesPercentage(self, language=None):
        if self.messageCount() > 0:
            percent = float(self.updatesCount(language)) / self.messageCount()
            percent *= 100
            percent = round(percent, 2)
        else:
            percent = 0
        return float(str(percent))

    def rosettaCount(self, language=None):
        # This method should be overrided by the objects that inherit from
        # this object.
        return 0

    def rosettaPercentage(self, language=None):
        if self.messageCount() > 0:
            percent = float(self.rosettaCount(language)) / self.messageCount()
            percent *= 100
            percent = round(percent, 2)
        else:
            percent = 0
        return float(str(percent))

    def translatedCount(self, language=None):
        return self.currentCount(language) + self.rosettaCount(language)

    def translatedPercentage(self, language=None):
        if self.messageCount() > 0:
            percent = float(self.translatedCount(language)) / self.messageCount()
            percent *= 100
            percent = round(percent, 2)
        else:
            percent = 0
        return float(str(percent))

    def untranslatedCount(self, language=None):
        untranslated = self.messageCount() - self.translatedCount(language)
        # We do a small sanity check so we don't return negative numbers.
        if untranslated < 0:
            return 0
        else:
            return untranslated

    def untranslatedPercentage(self, language=None):
        if self.messageCount() > 0:
            percent = float(self.untranslatedCount(language)) / self.messageCount()
            percent *= 100
            percent = round(percent, 2)
        else:
            percent = 100
        return float(str(percent))

    def nonUpdatesCount(self, language=None):
        nonupdates = self.currentCount() - self.updatesCount()
        if nonupdates < 0:
            return 0
        else:
            return nonupdates

    def nonUpdatesPercentage(self, language=None):
        if self.messageCount() > 0:
            percent = float(self.nonUpdatesCount(language)) / self.messageCount()
            percent *= 100
            percent = round(percent, 2)
        else:
            percent = 0
        return float(str(percent))

