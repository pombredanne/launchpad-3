# Copyright 2005 Canonical Ltd.  All rights reserved.

"""ISpecificationTarget browser views."""

__metaclass__ = type

__all__ = [
    'SpecificationTargetView',
    ]

from canonical.lp.dbschema import SpecificationStatus, SpecificationPriority
from canonical.launchpad.interfaces import ISpecificationTarget, IPerson

class SpecificationTargetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._plan = None
        self._dangling = None

    def categories(self):
        """This organises the specifications related to this target by
        "category", where a category corresponds to a particular spec
        status. It also determines the order of those categories, and the
        order of the specs inside each category. This is used for the +specs
        view.

        It is also used in IPerson, which is not an ISpecificationTarget but
        which does have a IPerson.specifications. In this case, it will also
        detect which set of specifications you want to see. The options are:

         - all specs (self.context.specifications)
         - created by this person (self.context.created_specs)
         - assigned to this person (self.context.assigned_specs)
         - for review by this person (self.context.review_specs)
         - specs this person must approve (self.context.approver_specs)
         - drafted by this person (self.context.drafted_specs)
         - subscribed by this person (self.context.subscriber_specs)

        """
        categories = {}
        if not IPerson.providedBy(self.context):
            specs = self.context.specifications
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
                specs = self.context.specifications
        for spec in specs:
            if categories.has_key(spec.status):
                category = categories[spec.status]
            else:
                category = {}
                category['status'] = spec.status
                category['specs'] = []
                categories[spec.status] = category
            category['specs'].append(spec)
        categories = categories.values()
        return sorted(categories, key=lambda a: a['status'].value)

    def getLatestSpecifications(self, quantity=5):
        """Return <quantity> latest specs created for this target. This
        is used by the +portlet-latestspecs view.
        """
        return self.context.specifications[:quantity]

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
        specs = set(self.context.specifications)
        # filter out the ones that are already implemented, or have been
        # declared obsolete or superceded
        specs = [spec for spec in specs if spec.status not in [
            SpecificationStatus.OBSOLETE, SpecificationStatus.SUPERCEDED,
            SpecificationStatus.IMPLEMENTED]]
        # sort the specs first by priority (most important first) then by
        # status (most complete first)
        specs = sorted(specs, key=lambda a: (-a.priority.value,
            a.status.value))
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


