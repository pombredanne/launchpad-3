# Copyright 2005 Canonical Ltd.  All rights reserved.

"""ISpecificationTarget browser views."""

__metaclass__ = type

__all__ = [
    'SpecificationTargetView',
    ]

from canonical.lp.dbschema import (
    SpecificationStatus, SpecificationPriority, SpecificationSort)

from canonical.launchpad.interfaces import ISpecificationTarget, IPerson

class SpecificationTargetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._plan = None
        self._dangling = None
        self._workload = None
        self._categories = None
        self._count = None
        self._specs = None
        self.listing_detailed = True
        self.listing_compact = False
        url = self.request.getURL()
        if '+createdspecs' in url:
            self.view_title = 'Created by %s' % self.context.title
        elif '+approverspecs' in url:
            self.view_title = 'For approval by %s' % self.context.title
        elif '+assignedspecs' in url:
            self.view_title = 'Assigned to %s' % self.context.title
        elif '+reviewspecs' in url:
            self.view_title = 'For review by %s' % self.context.title
        elif '+draftedspecs' in url:
            self.view_title = 'Drafted by %s' % self.context.title
        elif '+subscribedspecs' in url:
            self.view_title = 'Subscribed by %s' % self.context.title
        else:
            self.view_title = ''

    @property
    def specs(self):
        if self._specs is not None:
            return self._specs
        if not IPerson.providedBy(self.context):
            specs = self.context.specifications()
        else:
            # for a person, we need to figure out which set of specs to be
            # showing.

            # XXX sabdfl 07/09/05 we need to discuss this in UBZ
            url = self.request.getURL()
            if '+createdspecs' in url:
                specs = self.context.created_specs
            elif '+approverspecs' in url:
                specs = self.context.approver_specs
            elif '+assignedspecs' in url:
                specs = self.context.assigned_specs
            elif '+reviewspecs' in url:
                specs = self.context.review_specs
            elif '+draftedspecs' in url:
                specs = self.context.drafted_specs
            elif '+subscribedspecs' in url:
                specs = self.context.subscribed_specs
            else:
                specs = self.context.specifications()
        self._specs = specs
        # update listing style
        self._count = len(specs)
        if self._count > 5:
            self.listing_detailed = False
            self.listing_compact = True
        return self._specs

    @property
    def categories(self):
        """This organises the specifications related to this target by
        "category", where a category corresponds to a particular spec
        status. It also determines the order of those categories, and the
        order of the specs inside each category. This is used for the +specs
        view.

        It is also used in IPerson, which is not an ISpecificationTarget but
        which does have a IPerson.specifications. In this case, it will also
        detect which set of specifications you want to see. The options are:

         - all specs (self.context.specifications())
         - created by this person (self.context.created_specs)
         - assigned to this person (self.context.assigned_specs)
         - for review by this person (self.context.review_specs)
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

    @property
    def count(self):
        """Return the number of specs in this view."""
        if self._count is not None:
            return self._count
        # generating the spec list will set self._count
        speclist = self.specs
        return self._count

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

    def workload(self):
        """This code is copied in large part from browser/sprint.py. It may
        be worthwhile refactoring this to use a common code base.
        
        Return a structure that lists people, and for each person, the
        specs at on this target that for which they are the approver, the
        assignee or the drafter."""

        if self._workload is not None:
            return self._workload

        class MySpec:
            def __init__(self, spec, user):
                self.spec = spec
                self.assignee = False
                self.drafter = False
                self.approver = False
                if spec.assignee == user:
                    self.assignee = True
                if spec.drafter == user:
                    self.drafter = True
                if spec.approver == user:
                    self.approver = True

        class Group:
            def __init__(self, person):
                self.person = person
                self.specs = set()

            def by_priority(self):
                return sorted(self.specs, key=lambda a: a.spec.priority,
                    reverse=True)

            def add_spec(self, spec):
                for curr_spec in self.specs:
                    if curr_spec.spec == spec:
                        return
                self.specs.add(MySpec(spec, self.person))

        class Report:
            def __init__(self):
                self.contents = {}

            def _getGroup(self, person):
                group = self.contents.get(person.browsername, None)
                if group is not None:
                    return group
                group = Group(person)
                self.contents[person.browsername] = group
                return group

            def process(self, spec):
                """Make sure that this Report.contents has a Group for each
                person related to the spec, and that Group has the spec in
                the relevant list.
                """
                if spec.assignee is not None:
                    group = self._getGroup(spec.assignee)
                    group.add_spec(spec)
                if spec.drafter is not None:
                    self._getGroup(spec.drafter).add_spec(spec)
                if spec.approver is not None:
                    self._getGroup(spec.approver).add_spec(spec)

            def results(self):
                return [self.contents[key]
                    for key in sorted(self.contents.keys())]

        report = Report()
        for spec in self.specs:
            report.process(spec)

        self._workload = report.results()
        return self._workload



