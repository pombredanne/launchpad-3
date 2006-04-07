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
        self.listing_detailed = True
        self.listing_compact = False

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

        # Set a title for the "Goal" of any specs
        self.goaltitle = ''
        if IProduct.providedBy(self.context):
            self.goaltitle = 'Series'
        elif IDistribution.providedBy(self.context):
            self.goaltitle = 'Release'

    def specs(self):
        """This should be implemented in a subclass that knows how its
        context can filter its list of specs.
        """

        raise NotImplementedError

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
        plan = []
        specs = set(self.context.specifications())
        # filter out the ones that are already complete
        specs = [spec for spec in specs if not spec.is_complete]
        # sort the specs first by priority (most important first) then by
        # status (most complete first)
        specs = sorted(specs, key=lambda a: (a.priority, -a.status.value),
            reverse=True)
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


    @cachedproperty
    def OLD_specs(self):
        """The list of specs that are going to be displayed in this view.

        This method determines the appropriate filtering to be passed to
        context.specifications(). See IHasSpecifications.specifications
        for further details.

        The method can review the URL and decide what will be included,
        and what will not.

        The typical URL is of the form:

           ".../name1/+specs?role=creator&show=all"

        This method will interpret the show= part based on the kind of
        object that is the context of this request.
        """
        url = self.request.getURL()
        show = self.request.form.get('show', None)
        role = self.request.form.get('role', None)
        if IPerson.providedBy(self.context):
            # for a person, we need to figure out which set of specs to be
            # showing, mostly based on the relationship of the person to the
            # specs.
            if role == 'created':
                specs = self.context.created_specs
            elif role == 'approver':
                specs = self.context.approver_specs
            elif role == 'assigned':
                specs = self.context.assigned_specs
            elif role == 'feedback':
                specs = self.context.feedback_specs
            elif role == 'drafter':
                specs = self.context.drafted_specs
            elif role == 'subscribed':
                specs = self.context.subscribed_specs
            else:
                specs = shortlist(self.context.specifications())

            # now we want to filter the list based on whether or not we are
            # showing all of them or just the ones that are not complete
            if show != 'all':
                specs = [spec for spec in specs if not spec.is_complete]

        elif IProductSeries.providedBy(self.context) or \
             IDistroRelease.providedBy(self.context):
            # produce a listing for a product series or distrorelease

            specs = shortlist(self.context.specifications())

            # filtering here is based on whether or not the spec has been
            # approved or declined for this target
            if show == 'all':
                # we won't filter it if they ask for all specs
                pass
            elif show == 'declined':
                specs = [
                    spec
                    for spec in specs
                    if spec.goalstatus == SpecificationGoalStatus.DECLINED]
            elif show == 'proposed':
                specs = [
                    spec
                    for spec in specs
                    if spec.goalstatus == SpecificationGoalStatus.PROPOSED]
            else:
                # the default is to show only accepted specs
                specs = [
                    spec
                    for spec in specs
                    if spec.goalstatus == SpecificationGoalStatus.ACCEPTED]

        elif ISprint.providedBy(self.context):
            # process this as if it were a sprint

            spec_links = shortlist(self.context.specificationLinks())

            # filter based on whether the topics were deferred or accepted
            if show == 'deferred':
                specs = [
                    spec_link.specification
                    for spec_link in spec_links
                    if spec_link.status == SprintSpecificationStatus.DEFERRED]
            else:
                specs = [
                    spec_link.specification
                    for spec_link in spec_links
                    if spec_link.is_confirmed is True]

        else:
            # This is neither a person, nor a distrorelease, nor a product
            # series spec listing, nor a sprint
            specs = shortlist(self.context.specifications())

            # now we want to filter the list based on whether or not we are
            # showing all of them or just the ones that are not complete
            if show != 'all':
                specs = [spec for spec in specs if not spec.is_complete]

        return specs

