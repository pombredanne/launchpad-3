# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser code for Distro Release Languages."""

__metaclass__ = type

__all__ = ['DistroReleaseLanguageView']

from datetime import datetime

from zope.component import getUtility
from zope.interface import implements

import pytz

from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.helpers import DummyPOFile
from canonical.launchpad.interfaces import (ILaunchBag,
    IDistroReleaseLanguage)


class DistroReleaseLanguageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.form = self.request.form

class DummyDistroReleaseLanguage(RosettaStats):
    """
    Represents a DistroReleaseLanguage where we do not yet actually HAVE one
    for that language for this distro release.
    """
    implements(IDistroReleaseLanguage)

    def __init__(self, distrorelease, language):
        self.distrorelease = distrorelease
        self.language = language
        self.messageCount = distrorelease.messagecount
        self.dateupdated = datetime.now(tz=pytz.timezone('UTC'))
        self.translator_count = 0
        self.contributor_count = 0
        self.title = '%s translations of applications in %s, %s' % (
            self.language.englishname,
            self.distrorelease.distribution.displayname,
            self.distrorelease.title)

    @property
    def pofiles(self):
        """We need to pretend that we have pofiles, so we will use
        DummyPOFile's."""
        pofiles = []
        for potemplate in self.distrorelease.potemplates:
            pofiles.append(DummyPOFile(potemplate, self.language))
        return pofiles

    def currentCount(self):
        return 0

    def rosettaCount(self):
        return 0

    def updatesCount(self):
        return 0

    def nonUpdatesCount(self):
        return 0

    def translatedCount(self):
        return 0

    def untranslatedCount(self):
        return self.messageCount

    def currentPercentage(self):
        return 0.0

    def rosettaPercentage(self):
        return 0.0

    def updatesPercentage(self):
        return 0.0

    def nonUpdatesPercentage(self):
        return 0.0

    def translatedPercentage(self):
        return 0.0

    def untranslatedPercentage(self):
        return 100.0


