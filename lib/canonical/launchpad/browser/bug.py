
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.launchpad.database import BugAttachmentContainer, \
        BugExternalRefContainer, BugSubscriptionContainer, \
        BugWatchContainer, ProductBugAssignmentContainer, \
        SourcePackageBugAssignmentContainer, \
        BugProductInfestationContainer, \
        BugPackageInfestationContainer, Person, Bug, \
        BugsAssignedReport, BugContainer

from canonical.launchpad.interfaces import IPerson
        

def traverseBug(bug, request, name):
    if name == 'attachments':
        return BugAttachmentContainer(bug=bug.id)
    elif name == 'references':
        return BugExternalRefContainer(bug=bug.id)
    elif name == 'people':
        return BugSubscriptionContainer(bug=bug.id)
    elif name == 'watches':
        return BugWatchContainer(bug=bug.id)
    elif name == 'productassignments':
        return ProductBugAssignmentContainer(bug=bug.id)
    elif name == 'sourcepackageassignments':
        return SourcePackageBugAssignmentContainer(bug=bug.id)
    elif name == 'productinfestations':
        return BugProductInfestationContainer(bug=bug.id)
    elif name == 'packageinfestations':
        return BugPackageInfestationContainer(bug=bug.id)
    else:
       raise KeyError, name

def traverseBugs(bugcontainer, request, name):
    if name == 'assigned':
        return BugsAssignedReport()
    else:
        return BugContainer()[int(name)]


# TODO: It should be possible to specify all this via ZCML and not require
# the MaloneBugView class with its ViewPageTemplateFile attributes
class MaloneBugView(object):
    # XXX fix these horrific relative paths
    watchPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-watch.pt')
    productAssignmentPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-productassignment.pt')
    sourcepackageAssignmentPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-sourcepackageassignment.pt')
    productInfestationPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-productinfestation.pt')
    packageInfestationPortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-sourcepackageinfestation.pt')
    referencePortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-reference.pt')
    peoplePortlet = ViewPageTemplateFile(
        '../templates/portlet-bug-people.pt')


# Bug Reports
class BugsAssignedReportView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        # Default to showing bugs assigned to the logged in user.
        username = self.form.get('user', None)
        if username: self.user = Person.selectBy(name=username)[0]
        else:
            try: self.user = IPerson(self.request.principal)
            except TypeError: self.user = None
        self.context.user = self.user

    def userSelector(self):
        html = '<select name="user" onclick="form.submit()">\n'
        for person in self.allPeople():
            html = html + '<option value="'+person.name+'"'
            if person==self.user: html = html + ' selected="yes"'
            html = html + '>'
            html = html + person.browsername() + '</option>\n'
        html = html + '</select>\n'
        return html

    def allPeople(self):
        return Person.select()


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


