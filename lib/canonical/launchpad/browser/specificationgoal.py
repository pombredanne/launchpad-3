# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Views for Specification Goal Setting."""

__metaclass__ = type

from zope.component import getUtility
from zope.app.form.browser.add import AddView

from canonical.launchpad.browser.specificationtarget import (
    HasSpecificationsView)

from canonical.launchpad.interfaces import ISpecificationGoal

from canonical.lp.dbschema import (
    SpecificationGoalStatus, SpecificationFilter)

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import canonical_url, LaunchpadView
from canonical.launchpad.helpers import shortlist


__all__ = [
    'GoalSetView',
    ]


class GoalSetView(LaunchpadView):
    """Custom view class to process the results of this unusual page.

    It is unusual because we want to display multiple objects with
    checkboxes, then process the selected items, which is not the usual
    add/edit metaphor.
    """

    @cachedproperty
    def spec_filter(self):
        """This page always filters for specs which have been proposed
        for this goal.
        """
        return [SpecificationFilter.PROPOSED]

    def initialize(self):
        self.status_message = None
        self.process_form()

    def process_form(self):
        """Process the submitted form.

        Largely copied from webapp/generalform.py, without the
        schema processing bits because we are not rendering the form in the
        usual way. Instead, we are creating our own form in the page
        template and interpreting it here.
        """
        form = self.request.form

        if 'SUBMIT_CANCEL' in form:
            self.status_message = 'Cancelled'
            self.request.response.redirect(
                canonical_url(self.context)+'/+specs')
            return self.status_message

        if 'SUBMIT_ACCEPT' not in form and 'SUBMIT_DECLINE' not in form:
            self.status_message = ''
            return self.status_message

        if self.request.method == 'POST':
            if 'specification' not in form:
                self.status_message = (
                    'Please select specifications to accept or decline.')
                return self.status_message
            # determine if we are accepting or declining
            if 'SUBMIT_ACCEPT' in form:
                assert 'SUBMIT_DECLINE' not in form
                action = 'Accepted'
            else:
                assert 'SUBMIT_DECLINE' in form
                action = 'Declined'

        selected_specs = form['specification']
        if isinstance(selected_specs, unicode):
            # only a single item was selected, but we want to deal with a
            # list for the general case, so convert it to a list
            selected_specs = [selected_specs]

        if action == 'Accepted':
            action_fn = self.context.acceptSpecificationGoals
        else:
            action_fn = self.context.declineSpecificationGoals
        specs = [self.context.getSpecification(name) for name in selected_specs]
        leftover = action_fn(specs)

        # For example: "Accepted 26 specification(s)."
        self.status_message = '%s %d specification(s).' % (
            action, len(selected_specs))

        if leftover == 0:
            # they are all done, so redirect back to the spec listing page
            self.request.response.redirect(
                canonical_url(self.context)+'/+specs')

        return self.status_message

