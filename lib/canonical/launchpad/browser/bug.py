
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zope.interface import implements
from zope.schema.interfaces import IText
from zope.app.form.browser import TextAreaWidget, TextWidget

from canonical.launchpad.database import BugAttachmentSet, \
        BugExternalRefSet, BugSubscriptionSet, \
        BugWatchSet, ProductBugAssignmentSet, \
        SourcePackageBugAssignmentSet, \
        BugProductInfestationSet, \
        BugPackageInfestationSet, Person, Bug, \
        BugsAssignedReport, BugSet

from canonical.launchpad.interfaces import IPerson

from canonical.lp import dbschema

def traverseBug(bug, request, name):
    if name == 'attachments':
        return BugAttachmentSet(bug=bug.id)
    elif name == 'references':
        return BugExternalRefSet(bug=bug.id)
    elif name == 'cve':
        return CVERefSet(bug=bug.id)
    elif name == 'people':
        return BugSubscriptionSet(bug=bug.id)
    elif name == 'watches':
        return BugWatchSet(bug=bug.id)
    elif name == 'productassignments':
        return ProductBugAssignmentSet(bug=bug.id)
    elif name == 'packageassignments':
        return SourcePackageBugAssignmentSet(bug=bug.id)
    elif name == 'productinfestations':
        return BugProductInfestationSet(bug=bug.id)
    elif name == 'packageinfestations':
        return BugPackageInfestationSet(bug=bug.id)
    else:
       raise KeyError, name

def traverseBugs(bugcontainer, request, name):
    if name == 'assigned':
        return BugsAssignedReport()
    else:
        return BugSet()[int(name)]


# TODO: It should be possible to specify all this via ZCML and not require
# the BugView class with its ViewPageTemplateFile attributes
# (I think the browser:view directive allows this alread -- stub)
class BugView(object):
    # XXX fix these horrific relative paths
    watchPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-watch.pt')
    productAssignmentPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-productassignments.pt')
    sourcepackageAssignmentPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-packageassignments.pt')
    productInfestationPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-productinfestation.pt')
    packageInfestationPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-sourcepackageinfestation.pt')
    referencePortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-reference.pt')
    cvePortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-cve.pt')
    peoplePortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-people.pt')
    assignmentsHeadline = ViewPageTemplateFile(
        '../templates/portlet-bug-assignments-headline.pt')


class BugsCreatedByView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getAllPeople(self):
        return Person.select()

    def _getBugsForOwner(self, owner):
        bugs_created_by_owner = []
        if owner:
            persons = Person.select(Person.q.name == owner)
            if persons:
                person = persons[0]
                bugs_created_by_owner = Bug.select(Bug.q.ownerID == person.id)
        else:
            bugs_created_by_owner = Bug.select()

        return bugs_created_by_owner

    def getBugs(self):
        bugs_created_by_owner = self._getBugsForOwner(self.request.get("owner", ""))
        return bugs_created_by_owner



#
# WIDGETS
# XXX Mark Shuttleworth first put here because they were for Malone use,
# since they are beng generalised we should move them somewhere dedicated
# for fields, widgets.
#

# SummaryWidget
# A widget to capture a summary
class SummaryWidget(TextAreaWidget):

    implements(IText)

    width = 60
    height = 5


# TitleWidget
# A launchpad title widget... needs to be a little wider than a normal
# Textline
class TitleWidget(TextWidget):

    implements(IText)

    displayWidth = 60


