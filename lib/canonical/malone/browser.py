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
        BugProductInfestation, BugPackageInfestation, BugContainerBase

from canonical.database import sqlbase

# I18N support for Malone
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('malone')

from canonical.lp import dbschema

# Interface imports
from canonical.launchpad.interfaces import \
        IBug, IBugAttachment, \
        IBugContainer, IBugAttachmentContainer, IBugExternalRefContainer, \
        IBugSubscriptionContainer, ISourcePackageContainer, \
        IBugWatchContainer, IProductBugAssignmentContainer, \
        ISourcePackageBugAssignmentContainer, IBugProductInfestationContainer, \
        IBugPackageInfestationContainer, IPerson, \
        IBugExternalRefsView

class MaloneApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def update(self):
        '''XXX Mark Shuttleworth 20/10/04 I suspect this is vestigial and
           can be excised.
           Handle request and setup this view the way the templates expect it
        '''
        from sqlobject import OR, LIKE, CONTAINSSTRING, AND
        if self.request.form.has_key('query'):
            # TODO: Make this case insensitive
            s = self.request.form['query']
            self.results = SourcePackage.select(AND(
                SourcePackage.q.sourcepackagenameID == SourcePackageName.q.id,
                OR(
                    CONTAINSSTRING(SourcePackageName.q.name, s),
                    CONTAINSSTRING(SourcePackage.q.shortdesc, s),
                    CONTAINSSTRING(SourcePackage.q.description, s)
                    )
                ))
            self.noresults = not self.results
        else:
            self.noresults = False
            self.results = []

