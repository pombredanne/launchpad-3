__metaclass__ = type

from zope.schema.vocabulary import getVocabularyRegistry
from zope.component import getUtility

from sqlobject.sqlbuilder import AND, IN, ISNULL, OR, SQLOp

from canonical.launchpad.browser.bug import BugView
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import IPerson, IPersonSet
from canonical.lp import dbschema
from canonical.launchpad.vocabularies import ValidPersonVocabulary, \
     ProductVocabulary, SourcePackageNameVocabulary
from canonical.database.sqlbase import quote
from canonical.launchpad.searchbuilder import NULL

# Bug Reports
class BugTasksReportView:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.user = None

        # default to showing bugs assigned to the logged in user.
        username = self.form.get('name', None)
        if username:
            self.user = getUtility(IPersonSet).getByName(username)
        else:
            # XXX: Brad Bollenbach, 2005-03-30: Why does this seem
            # to set self.user to something other than None even
            # when viewed by an anonymous user? Investigate.
            self.user = IPerson(self.request.principal)

        # default to showing even wishlist bugs
        self.minseverity = int(self.form.get('minseverity', 0))
        self.minpriority = int(self.form.get('minpriority', 0))
        if self.form.get('showclosed', None) == 'yes':
            self.showclosed = True
        else:
            self.showclosed = False

    def maintainedPackageBugs(self):
        return self.context.maintainedPackageBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    def maintainedProductBugs(self):
        return self.context.maintainedProductBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    def packageAssigneeBugs(self):
        return self.context.packageAssigneeBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    def productAssigneeBugs(self):
        return self.context.productAssigneeBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    def assignedBugs(self):
        return self.context.assignedBugs(
            self.user, self.minseverity, self.minpriority, self.showclosed)

    # TODO: replace this with a smart vocabulary and widget
    def userSelector(self):
        html = '<select name="name">\n'
        for person in self.allPeople():
            html = html + '<option value="'+person.name+'"'
            if person==self.user:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + person.browsername() + '</option>\n'
        html = html + '</select>\n'
        return html

    # TODO: replace this with a smart vocabulary and widget
    def severitySelector(self):
        html = '<select name="minseverity">\n'
        for item in dbschema.BugSeverity.items:
            html = html + '<option value="' + str(item.value) + '"'
            if item.value==self.minseverity:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + str(item.title)
            html = html + '</option>\n'
        html = html + '</select>\n'
        return html

    # TODO: replace this with a smart vocabulary and widget
    def prioritySelector(self):
        html = '<select name="minpriority">\n'
        for item in dbschema.BugPriority.items:
            html = html + '<option value="' + str(item.value) + '"'
            if item.value==self.minpriority:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + str(item.title)
            html = html + '</option>\n'
        html = html + '</select>\n'
        return html

    def showClosedSelector(self):
        html = '<input type="checkbox" id="showclosed" name="showclosed" value="yes"'
        if self.showclosed:
            html = html + ' checked="yes"'
        html = html + ' />'
        return html

    def allPeople(self):
        return getUtility(IPersonSet).search(password = NULL)

# XXX: 2004-11-13, Brad Bollenbach: Much of the code in BugTasksView
# is a dirty hack in the abscense of a more clean way of handling generating
# non-add, non-edit forms in Zope 3. I had a chat with SteveA on this subject
# and it looks like a browser:form directive will be introduced early next week
# in which case most of this hackishness can go away.
# XXX: 2004-12-02, Stuart Bishop: I'm not sure what this class is doing in here
# since it is actually a view on IBugSet.
class BugTasksView:

    DEFAULT_STATUS = (
        dbschema.BugTaskStatus.NEW.value,
        dbschema.BugTaskStatus.ACCEPTED.value)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.batch = Batch(list(self.search()),
                           int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

        # XXX: Brad Bollenbach, 2005-03-10: Effectively "disable"
        # the Anorak Search Page for now by redirecting to the
        # Malone front page. We'll reenable this page if user
        # feedback necessitates.
        self.request.response.redirect("/malone")

    def search(self):
        """Find the bug tasks the user wants to see."""
        # XXX: Brad Bollenbach, 2005-03-31: Cut out a huge chunk
        # of code here because this view should no longer be used.
        # I will fully rip this out in the next round of refactoring
        # (because I'm in the middle of refactoring something else
        # right now, and ripping this out right now will break other
        # things.)
        return []

    def status_message(self):
        # XXX: Brad Bollenbach, 2004-11-30: This method is a bit of a dirty
        # hack at outputting a useful message if a bug has just been added, in
        # lieu of a more general status message mechanism that avoids defacement
        # attacks (e.g. http://www.example.com?status_message=You+have+been+hax0red).
        bugadded = self.request.get('bugadded', None)
        if bugadded:
            try:
                int(bugadded)
                return 'Successfully added <a href="%s">bug # %s</a>. Thank you!' % (
                    bugadded, bugadded)
            except ValueError, err:
                pass

        return ''

    def submitted(self):
        return self.request.get('search', None)

    def people(self):
        """Return the list of people in Launchpad."""
        return ValidPersonVocabulary(None)

    def statuses(self):
        """Return the list of bug task statuses."""
        return dbschema.BugTaskStatus.items

    def packagenames(self):
        """Return the list of source package names."""
        return SourcePackageNameVocabulary(None)

    def advanced(self):
        '''Return 1 if the form should be rendered in advanced mode, 0
        otherwise'''
        req = self.request
        marker = object()
        if req.get('advanced_submit', marker) is not marker:
            return 1
        if req.get('simple_submit', marker) is not marker:
            return 0
        if int(req.get('advanced', 0)):
            return 1
        return 0
    advanced = property(advanced)

    def products(self):
        """Return the list of products."""
        return ProductVocabulary(None)
