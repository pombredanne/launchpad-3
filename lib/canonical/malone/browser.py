# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C

from datetime import datetime
from email.Utils import make_msgid

from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import TextLine, Int, Choice
from zope.event import notify

from canonical.launchpad.database import \
        SourcePackage, SourcePackageName, BinaryPackage, \
        BugTracker, BugsAssignedReport, BugWatch, Product, Person, EmailAddress, \
        Bug, BugAttachment, BugExternalRef, BugSubscription, \
        ProductBugAssignment, SourcePackageBugAssignment, \
        BugProductInfestation, BugPackageInfestation, BugSetBase

from canonical.database import sqlbase

# I18N support for Malone
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('malone')

from canonical.lp import dbschema

# Interface imports
from canonical.launchpad.interfaces import \
        IBug, IBugAttachment, \
        IBugSet, IBugAttachmentSet, IBugExternalRefSet, \
        IBugSubscriptionSet, ISourcePackageSet, \
        IBugWatchSet, IProductBugAssignmentSet, \
        ISourcePackageBugAssignmentSet, IBugProductInfestationSet, \
        IBugPackageInfestationSet, IPerson, \
        IBugExternalRefsView

class MaloneApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

