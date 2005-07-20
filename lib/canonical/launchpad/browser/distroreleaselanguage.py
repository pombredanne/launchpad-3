# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser code for Distro Release Languages."""

__metaclass__ = type

__all__ = ['DistroReleaseLanguageView']

from zope.component import getUtility

from canonical.launchpad.interfaces import (ILaunchBag,
    IDistroReleaseLanguage)


class DistroReleaseLanguageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.form = self.request.form

