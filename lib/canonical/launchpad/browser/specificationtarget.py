# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ISpecificationTarget browser views."""

__metaclass__ = type

__all__ = [
    'HasSpecificationsView',
    'SpecificationTargetView',
    ]

from canonical.lp.dbschema import (
    SpecificationSort, SpecificationStatus, SprintSpecificationStatus,
    SpecificationGoalStatus, SpecificationFilter)

from canonical.launchpad.interfaces import (
    ISprint, IPerson, IProduct, IDistribution, IProductSeries,
    IDistroRelease)

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.helpers import shortlist
from canonical.cachedproperty import cachedproperty


class HasSpecificationsView(LaunchpadView):
    """Base class for several context-specific views that involve lists of
    specifications.

    This base class knows how to handle and represent lists of
    specifications, produced by a method view.specs(). The individual class
    view objects each implement that method in a way that is appropriate for
    them, because they each want to filter the list of specs in different
    ways. For example, in the case of PersonSpecsView, you want to filter
    based on the relationship the person has to the specs. In the case of a
    ProductSpecsView you want to filter primarily based on the completeness
    of the spec.
    """

    def initialize(self):
        self._plan = None
        self._dangling = None
        self._categories = None

        url = self.request.getURL()
        # XXX: SteveAlexander, 2006-03-06.  This url-sniffing view_title
        #      setting code is not tested.  It doesn't appear to be used
        #      either.
        if 'created' in url:
            self.view_title = 'Created by %s' % self.context.title
        elif 'approver' in url:
            self.view_title = 'For approval by %s' % self.context.title
        elif 'assigned' in url:
            self.view_title = 'Assigned to %s' % self.context.title
        elif 'feedback' in url:
            self.view_title = 'Need feedback from %s' % self.context.title
        elif 'drafted' in url:
            self.view_title = 'Drafted by %s' % self.context.title
        elif 'subscribed' in url:
            self.view_title = 'Subscribed by %s' % self.context.title
        else:
            self.view_title = ''

    def specs(self):
        """This should be implemented in a subclass that knows how its
        context can filter its list of specs.
        """

        raise NotImplementedError

    @cachedproperty
    def documentation(self):
        filter = [SpecificationFilter.COMPLETE,
                  SpecificationFilter.INFORMATIONAL]
        return shortlist(self.context.specifications(filter=filter))

    @property
    def categories(self):
        """This organises the specifications related to this target by
        "category", where a category corresponds to a particular spec
        status. It also determines the order of those categories, and the
        order of the specs inside each category.

        It is also used in IPerson, which is not an ISpecificationTarget but
        which does have a IPerson.specifications. In this case, it will also
        detect which set of specifications you want to see. The options are:

         - all specs (self.context.specifications())
         - created by this person (self.context.created_specs)
         - assigned to this person (self.context.assigned_specs)
         - for review by this person (self.context.feedback_specs)
         - specs this person must approve (self.context.approver_specs)
         - drafted by this person (self.context.drafted_specs)
         - subscribed by this person (self.context.subscriber_specs)

        """
        if self._categories is not None:
            return self._categories
        categories = {}
        for spec in self.specs:
            if categories.has_key(spec.status):
                category = categories[spec.status]
            else:
                category = {}
                category['status'] = spec.status
                category['specs'] = []
                categories[spec.status] = category
            category['specs'].append(spec)
        categories = categories.values()
        self._categories = sorted(categories, key=lambda a: a['status'].value)
        return self._categories

    def getLatestSpecifications(self, quantity=5):
        """Return <quantity> latest specs created for this target. This
        is used by the +portlet-latestspecs view.
        """
        return self.context.specifications(sort=SpecificationSort.DATE,
            quantity=quantity)

    def specPlan(self):
        """Return the current sequence of recommended spec implementations,
        based on their priority and dependencies.
        """
        if self._plan is None:
            # we have not done this before so make the plan
            self.makeSpecPlan()
        return self._plan

    def danglingSpecs(self):
        """Return the specs that are currently in a messy state because
        their dependencies do not allow them to be implemented (circular
        deps, for example.
        """
        if self._dangling is None:
            # we have not done this before so figure out if any are dangling
            self.makeSpecPlan()
        return self._dangling

    def makeSpecPlan(self):
        """Figure out what the best sequence of implementation is for the
        specs currently in the queue for this target. Save the plan in
        self._plan, and put any dangling specs in self._dangling.
        """
        # XXX sabdfl 2006-04-07 this is incomplete and will not build a
        # proper comprehensive roadmap
        plan = []
        filter = [SpecificationFilter.INCOMPLETE]
        specs = set(self.context.specifications(filter=filter))
        found_spec = True
        while found_spec:
            found_spec = False
            for spec in specs:
                if spec in plan:
                    continue
                if not spec.dependencies:
                    found_spec = True
                    plan.append(spec)
                    continue
                all_clear = True
                for depspec in spec.dependencies:
                    if depspec not in plan:
                        all_clear = False
                        break
                if all_clear:
                    found_spec = True
                    plan.append(spec)
        # ok. at this point, plan contains the ones that can move
        # immediately. we need to find the dangling ones
        dangling = []
        for spec in specs:
            if spec not in plan:
                dangling.append(spec)
        self._plan = plan
        self._dangling = dangling


class SpecificationTargetView(HasSpecificationsView):

    @cachedproperty
    def specs(self):
        """The list of specs that are going to be displayed in this view.

        This method determines the appropriate filtering to be passed to
        context.specifications(). See IHasSpecifications.specifications
        for further details.

        The method can review the URL and decide what will be included,
        and what will not.

        This particular implementation is used for IDistribution and
        IProduct, the two objects which are an ISpecificationTarget.

        The typical URL is of the form:

           ".../name1/+specs?show=complete"

        This method will interpret the show= part based on the kind of
        object that is the context of this request.
        """
        show = self.request.form.get('show', None)
        informational = self.request.form.get('informational', False)

        filter = []

        # filter on completeness, show incomplete if nothing is said
        if show == 'all':
            filter.append(SpecificationFilter.ALL)
        elif show == 'complete':
            filter.append(SpecificationFilter.COMPLETE)
        elif show == None or show == 'incomplete':
            filter.append(SpecificationFilter.INCOMPLETE)

        # filter for informational status
        if informational is not False:
            filter.append(SpecificationFilter.INFORMATIONAL)

        specs = self.context.specifications(filter=filter)

        return specs

    @property
    def goaltitle(self):
        if IProduct.providedBy(self.context):
            return 'Series'
        elif IDistribution.providedBy(self.context):
            return 'Release'

