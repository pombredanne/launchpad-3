# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for Specification Goal Setting."""

__metaclass__ = type

from zope.app.form.browser.add import AddView

from zope.component import getUtility

from canonical.launchpad.interfaces import ISpecificationGoal

from canonical.lp.dbschema import SpecificationTargetStatus

from canonical.launchpad.webapp import canonical_url


__all__ = [
    'GoalSetView',
    ]


class GoalSetView:

    def __init__(self, context, request):
        """A custom little view class to process the results of this unusual
        page. It is unusual because we want to display multiple objects with
        checkboxes, then process the selected items, which is not the usual
        add/edit metaphor."""
        self.context = context
        self.request = request
        self.process_status = None
        self._count = None
        self._specs = None

    @property
    def specs(self):
        """Return the specifications which have been proposed for this goal.
        For the moment, we just filter the list in Python.
        """
        if self._specs is not None:
            return self._specs
        _specs = list(self.context.specifications())
        self._specs = [spec for spec in _specs
            if spec.targetstatus == SpecificationTargetStatus.PROPOSED]
        return self._specs

    @property
    def count(self):
        """Return the number of specifications to be listed."""
        if self._count is not None:
            return self._count
        self._count = len(self.specs)
        return self._count

    def process_form(self):
        """Largely copied from webapp/generalform.py, without the
        schema processing bits because we are not rendering the form in the
        usual way. Instead, we are creating our own form in the page
        template and interpreting it here."""

        if self.process_status is not None:
            # We've been called before. Just return the status we previously
            # computed.
            return self.process_status

        if 'cancel' in self.request:
            self.process_status = 'Cancelled'
            self.request.response.redirect(canonical_url(self.context)+'/+specs')
            return self.process_status

        if "FORM_SUBMIT" not in self.request:
            self.process_status = ''
            return self.process_status

        if self.request.method == 'POST':
            if 'specification' not in self.request:
                self.process_status = ('Please select specifications '
                                       'to accept or decline.')
                return self.process_status
            # determine if we are accepting or declining
            if self.request.form.get('FORM_SUBMIT', None) == 'Accept':
                action = 'Accepted'
            else:
                action = 'Declined'

        selected_specs = self.request['specification']
        if isinstance(selected_specs, unicode):
            # only a single item was selected, but we want to deal with a
            # list for the general case, so convert it to a list
            selected_specs = [selected_specs,]
        
        number_done = 0
        for specname in selected_specs:
            spec = self.context.getSpecification(specname)
            if action == 'Accepted':
                self.context.acceptSpecificationGoal(spec)
            else:
                self.context.declineSpecificationGoal(spec)
            number_done += 1

        self.process_status = '%s %d specification(s).' % (action, number_done)

        if self.count == 0:
            # they are all done, so redirect back to the spec listing page
            self.request.response.redirect(canonical_url(self.context)+'/+specs')

        return self.process_status

