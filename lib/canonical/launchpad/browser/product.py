# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent
from zope.component import getUtility
import zope.security.interfaces

from sqlobject.sqlbuilder import AND, IN, ISNULL

from canonical.lp import dbschema
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.database.sqlbase import quote
from canonical.launchpad.vocabularies import ValidPersonVocabulary, \
     MilestoneVocabulary

from canonical.launchpad.database import Product, ProductSeriesSet, Bug, \
     BugFactory, ProductMilestoneSet, Milestone, BugTask, SourceSourceSet,\
     Person

from canonical.launchpad.interfaces import IPerson, IProduct, IProductSet
from canonical.launchpad.browser.productrelease import newProductRelease

#
# Traversal functions that help us look up something
# about a project or product
#
def traverseProduct(product, request, name):
    if name == '+sources':
        return SourceSourceSet()
    elif name == '+series':
        return ProductSeriesSet(product = product)
    elif name == 'milestones':
        return ProductMilestoneSet(product = product)
    else:
        return product.getRelease(name)

#
# A View Class for Product
#
class ProductView:

    translationsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-translations.pt')

    latestBugPortlet = ViewPageTemplateFile(
        '../templates/portlet-latest-bugs.pt')

    branchesPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-branches.pt')

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-details.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-actions.pt')

    projectPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-project.pt')

    milestonePortlet = ViewPageTemplateFile(
        '../templates/portlet-product-milestones.pt')

    def __init__(self, context, request):
        self.context = context
        self.product = context
        self.request = request
        self.form = request.form

    def edit(self):
        """
        Update the contents of a Product. This method is called by a
        tal:dummy element in a page template. It checks to see if a
        form has been submitted that has a specific element, and if
        so it continues to process the form, updating the fields of
        the database as it goes.
        """
        # check that we are processing the correct form, and that
        # it has been POST'ed
        form = self.form
        if form.get("Update") != "Update Product":
            return
        if self.request.method != "POST":
            return
        # Extract details from the form and update the Product
        self.context.displayname = form['displayname']
        self.context.title = form['title']
        self.context.shortdesc = form['shortdesc']
        self.context.description = form['description']
        self.context.homepageurl = form['homepageurl']
        notify(ObjectModifiedEvent(self.context))
        # now redirect to view the product
        self.request.response.redirect(self.request.URL[-1])

    def sourcesources(self):
        return iter(self.context.sourcesources())

    def newSourceSource(self):
        form = self.form
        if (form.get("Register") != "Register Revision Control System"):
            return
        if self.request.method != "POST":
            return
        owner = IPerson(self.request.principal)
        #XXX: cprov 20050112
        # SteveA comments:
        # Passing form is only slightly more evil than passing **kw.
        # I'd rather see the correct keyword arguments passed in explicitly.
        #
        # Avoid passing obscure arguments as self.form
        ss = self.context.newSourceSource(form, owner)
        self.request.response.redirect('+sources/'+ form['name'])

    def newProductRelease(self):
        # default owner is the logged in user
        owner = IPerson(self.request.principal)
        #XXX: cprov 20050112
        # Avoid passing obscure arguments as self.form
        pr = newProductRelease(self.form, self.context, owner)
 
    def newseries(self):
        #
        # Handle a request to create a new series for this product.
        # The code needs to extract all the relevant form elements,
        # then call the ProductSeries creation methods.
        #
        if not self.form.get("Register") == "Register Series":
            return
        if not self.request.method == "POST":
            return
        #XXX: cprov 20050112
        # Avoid passing obscure arguments as self.form
        series = self.context.newseries(self.form)
        # now redirect to view the page
        self.request.response.redirect('+series/'+series.name)

    def latestBugs(self, quantity=5):
        """Return <quantity> latest bugs reported against this product."""
        buglist = self.context.bugs
        # Sort the bugs by datecreated and return the last <quantity> bugs.
        bugsdated = [(bugass.datecreated, bugass) for bugass in buglist]
        bugsdated.sort()
        last_few_bugs = bugsdated[-quantity:]
        return [bugass for sortkey, bugass in last_few_bugs]

# XXX cprov 20050107
# This class needs revision for:
#  * not using BugTask directly
#  * code improves
#  * use Authorization component
class ProductBugsView:
    DEFAULT_STATUS = (
        int(dbschema.BugAssignmentStatus.NEW),
        int(dbschema.BugAssignmentStatus.ACCEPTED))

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.batch = Batch(
            self.bugassignment_search(), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

    def bugassignment_search(self):
        ba_params = []

        param_searchtext = self.request.get('searchtext')
        if param_searchtext:
            try:
                int_param_searchtext = int(param_searchtext)
            except ValueError:
                # Use full text indexing. We can't use like to search text
                # or descriptions since it won't use indexes.
                # XXX: Stuart Bishop, 2004-12-02 Pull this commented code
                # after confirming if we stick with tsearch2

                # XXX: Brad Bollenbach, 2004-11-26:
                # I always found it particularly
                # unhelpful that sqlobject doesn't have this by default, for DB
                # backends that support it.
                #
                # def ILIKE(expr, string):
                #    return SQLOp("ILIKE", expr, string)

                # looks like user wants to do a text search of
                # title/shortdesc/description
                #
                # searchtext = '%' + param_searchtext + '%'
                # bugs = Bug.select(
                #     OR(ILIKE(Bug.q.title, searchtext),
                #        ILIKE(Bug.q.shortdesc, searchtext),
                #        ILIKE(Bug.q.description, searchtext)))
                
                bugs = Bug.select('fti @@ ftq(%s)' % quote(param_searchtext))
                bugids = [bug.id for bug in bugs]
                if bugids:
                    ba_params.append(IN(BugTask.q.bugID, bugids))
                else:
                    return []

            else:
                self.request.response.redirect("/malone/bugs/" +
                                               int_param_searchtext)

        param_status = self.request.form.get('status', self.DEFAULT_STATUS)
        if param_status and param_status != 'all':
            status = []
            if isinstance(param_status, (list, tuple)):
                status = param_status
            else:
                status = [param_status]
            ba_params.append(IN(BugTask.q.status, status))

        param_assignee = self.request.get('assignee')
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

        param_target = self.request.get('target')
        if param_target and param_target not in ('all', 'unassigned'):
            targets = []
            if isinstance(param_target, (list, tuple)):
                targets = Milestone.select(IN(Milestone.q.name, param_target))
            else:
                targets = Milestone.select(Milestone.q.name == param_target)

            if targets:
                targets = [t.id for t in targets]

            ba_params.append(
                IN(BugTask.q.milestoneID, targets))
        elif param_target == 'unassigned':
            ba_params.append(ISNULL(BugTask.q.milestoneID))

        ba_params.append(BugTask.q.productID == self.context.id)

        if ba_params:
            ba_params = [AND(*ba_params)]

        return BugTask.select(*ba_params)

    def assignment_columns(self):
        return [
            "id", "title", "milestone", "status", "priority", "severity",
            "submittedon", "submittedby", "assignedto", "actions"]

    def assign_to_milestones(self):
        if self.request.principal:
            if self.context.owner.id == self.request.principal.id:
                milestone_name = self.request.get('milestone')
                if milestone_name:
                    milestone = Milestone.byName(milestone_name)
                    if milestone:
                        taskids = self.request.get('task')
                        if taskids:
                            if not isinstance(taskids, (list, tuple)):
                                taskids = [taskids]

                            tasks = [BugTask.get(taskid) for taskid in taskids]
                            for task in tasks:
                                task.milestone = milestone
       
    def people(self):
        """Return the list of people in Launchpad."""
        # the vocabulary doesn't need context since the
        # ValidPerson is independent of it in LP
        return ValidPersonVocabulary(None)
    
    def milestones(self):
        """Return the list of milestones for this product."""
        # Produce an empty context 
        class HackedContext:
            pass
        
        context = HackedContext()
        # Set context.product as required by Vocabulary
        context.product = self.context
        # Pass the designed context
        return MilestoneVocabulary(context)

    def statuses(self):
        """Return the list of bug assignment statuses."""
        return dbschema.BugAssignmentStatus.items


class ProductFileBugView(AddView):

    __used_for__ = IProduct

    #XXX cprov 20050107
    # Can we use the IBug instead of the content class ?
    ow = CustomWidgetFactory(ObjectWidget, Bug)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw
    
    def __init__(self, context, request):
        self.request = request
        self.context = context
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the bug
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized(
                "Need an authenticated bug owner")
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value
        kw['product'] = self.context
        # create the bug
        # XXX cprov 20050112
        # Try to avoid passing **kw, it is unreadable
        # Pass the keyword explicitly ...
        bug = BugFactory(**kw)
        notify(ObjectCreatedEvent(bug))
        return bug

    def nextURL(self):
        return self._nextURL
 

class ProductSetView:

    __used_for__ = IProductSet

    def __init__(self, context, request):
        
        self.context = context
        self.request = request
        form = self.request.form
        self.soyuz = form.get('soyuz')
        self.rosetta = form.get('rosetta')
        self.malone = form.get('malone')
        self.bazaar = form.get('bazaar')
        self.text = form.get('text')
        self.searchrequested = False
        if (self.text is not None or
            self.bazaar is not None or 
            self.malone is not None or 
            self.rosetta is not None or 
            self.soyuz is not None):
            self.searchrequested = True
        self.results = None
        self.gotmatches = 0


    def searchresults(self):
        """Use searchtext to find the list of Products that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(text=self.text,
                                               bazaar=self.bazaar,
                                               malone=self.malone,
                                               rosetta=self.rosetta,
                                               soyuz=self.soyuz)
        self.gotmatches = len(list(self.results))
        return self.results



class ProductSetAddView(AddView):

    __used_for__ = IProductSet

    ow = CustomWidgetFactory(ObjectWidget, Bug)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the product
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized(
                "Need an authenticated bug owner")
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value
        kw['owner'] = owner
        # grab a ProductSet utility 
        product_util = getUtility(IProductSet)
        # create a brand new Product
        # XXX cprov 20050112
        # Don't use collapsed dict as argument, use the
        # expanded  
        product = product_util.createProduct(**kw)
        notify(ObjectCreatedEvent(product))
        self._nextURL = kw['name']
        return product

    def nextURL(self):
        return self._nextURL


