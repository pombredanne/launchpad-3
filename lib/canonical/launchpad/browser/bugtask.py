__metaclass__ = type

from sqlobject.sqlbuilder import AND, IN, ISNULL, OR, SQLOp

from zope.schema.vocabulary import getVocabularyRegistry

from canonical.launchpad.browser.bug import BugView
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.database import Bug, BugTask, Person
from canonical.lp import dbschema
from canonical.launchpad.vocabularies import ValidPersonVocabulary, \
     ProductVocabulary, SourcePackageVocabulary, SourcePackageNameVocabulary
from canonical.database.sqlbase import quote

# Bug Reports
class BugTasksReportView:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        # default to showing bugs assigned to the logged in user.
        username = self.form.get('name', None)
        if username: self.context.user = Person.selectBy(name=username)[0]
        else:
            try: self.context.user = IPerson(self.request.principal)
            except TypeError: pass
        # default to showing even wishlist bugs
        self.context.minseverity = int(self.form.get('minseverity', 0))
        self.context.minpriority = int(self.form.get('minpriority', 0))
        if self.form.get('showclosed', None)=='yes':
            self.context.showclosed = True


    # TODO: replace this with a smart vocabulary and widget
    def userSelector(self):
        html = '<select name="name">\n'
        for person in self.allPeople():
            html = html + '<option value="'+person.name+'"'
            if person==self.context.user:
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
            if item.value==self.context.minseverity:
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
            if item.value==self.context.minpriority:
                html = html + ' selected="yes"'
            html = html + '>'
            html = html + str(item.title)
            html = html + '</option>\n'
        html = html + '</select>\n'
        return html

    def showClosedSelector(self):
        html = '<input type="checkbox" id="showclosed" name="showclosed" value="yes"'
        if self.context.showclosed:
            html = html + ' checked="yes"'
        html = html + ' />'
        return html

    def allPeople(self):
        return Person.select('password IS NOT NULL')

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
        ba_params = []

        param_searchtext = self.request.get('searchtext', None)
        if param_searchtext:
            try:
                int(param_searchtext)
                self.request.response.redirect("/malone/bugs/" + param_searchtext)
            except ValueError:
                """
                Use full text indexing. We can't use like to search text
                or descriptions since it won't use indexes.
                XXX: Stuart Bishop, 2004-12-02 Pull this commented code
                after confirming if we stick with tsearch2

                # XXX: Brad Bollenbach, 2004-11-26: I always found it particularly
                # unhelpful that sqlobject doesn't have this by default, for DB
                # backends that support it.
                def ILIKE(expr, string):
                    return SQLOp("ILIKE", expr, string)

                # looks like user wants to do a text search of
                # title/shortdesc/description
                searchtext = '%' + param_searchtext + '%'
                bugs = Bug.select(
                    OR(ILIKE(Bug.q.title, searchtext),
                       ILIKE(Bug.q.shortdesc, searchtext),
                       ILIKE(Bug.q.description, searchtext)))
                """
                bugs = Bug.select('fti @@ ftq(%s)' % quote(param_searchtext))
                bugids = [bug.id for bug in bugs]
                if bugids:
                    ba_params.append(IN(BugTask.q.bugID, bugids))
                else:
                    return []

        param_status = self.request.get('status', self.DEFAULT_STATUS)
        if param_status and param_status != 'all':
            status = []
            if isinstance(param_status, (list, tuple)):
                status = param_status
            else:
                status = [param_status]
            ba_params.append(IN(BugTask.q.status, status))

        param_severity = self.request.get('severity', None)
        if param_severity and param_severity != 'all':
            severity = []
            if isinstance(param_severity, (list, tuple)):
                severity = param_severity
            else:
                severity = [param_severity]
            ba_params.append(IN(BugTask.q.severity, severity))

        param_assignee = self.request.get('assignee', None)
        if param_assignee and param_assignee not in ('all', 'unassigned'):
            assignees = []
            if isinstance(param_assignee, (list, tuple)):
                people = Person.select(IN(Person.q.name, param_assignee))
            else:
                people = Person.select(Person.q.name == param_assignee)

            if people:
                assignees = [p.id for p in people]

            ba_params.append(
                IN(BugTask.q.assigneeID, assignees))
        elif param_assignee == 'unassigned':
            ba_params.append(ISNULL(BugTask.q.assigneeID))

        if self.request.get('submitter', None) and self.request['submitter'] != 'all':
            submitters = []
            if isinstance(self.request['submitter'], (list, tuple)):
                people = Person.select(IN(Person.q.name, self.request['submitter']))
            else:
                people = Person.select(Person.q.name == self.request['submitter'])

            if people:
                submitters = [p.id for p in people]

            ba_params.append(
                IN(BugTask.q.ownerID, submitters))

        if self.request.get('product', None) and self.request['product'] != 'all':
            product_ids = []
            if isinstance(self.request['product'], (list, tuple)):
                product_tokens = self.request['product']
            else:
                product_tokens = [self.request['product']]

            vr = getVocabularyRegistry()
            pv = vr.get(None, "Product")
            for product_token in product_tokens:
                term = pv.getTermByToken(product_token)
                product_ids.append(term.value.id)

            ba_params.append(IN(BugTask.q.productID, product_ids))

        if self.request.get('sourcepackagename', None) and self.request['sourcepackagename'] != 'all':
            sourcepackagenames = []
            if isinstance(self.request['sourcepackagename'], (list, tuple)):
                sourcepackagenames = self.request['sourcepackagename']
            else:
                sourcepackagenames = [self.request['sourcepackagename']]
            ba_params.append(IN(BugTask.q.sourcepackagenameID, sourcepackagenames))

        if ba_params:
            ba_params = [AND(*ba_params)]

        return BugTask.select(*ba_params)

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
