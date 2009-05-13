# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationDependency."""

__metaclass__ = type

__all__ = [
    'SpecificationDependencyAddView',
    'SpecificationDependencyRemoveView',
    ]

from canonical.launchpad import _
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView)
from canonical.widgets.popup import SinglePopupWidget
from lp.blueprints.interfaces.specificationdependency import (
    ISpecificationDependency, ISpecificationDependencyRemoval)

from zope.formlib import form
from zope.schema import Choice


class SpecificationDependencyAddView(LaunchpadFormView):
    schema = ISpecificationDependency
    field_names = ['dependency']
    label = _('Depends On')
    custom_widget('dependency', SinglePopupWidget)

    def setUpFields(self):
        """Override the setup to define own fields."""
        self.form_fields = form.Fields(
            Choice(
                __name__='dependency',
                title=_(u'Depends On'),
                vocabulary='SpecificationDepCandidates',
                required=True,
                description=_(
                    "If another blueprint needs to be fully implemented "
                    "before this feature can be started, then specify that "
                    "dependency here so Launchpad knows about it and can "
                    "give you an accurate project plan.")),
            render_context=self.render_context)

    def validate(self, data):
        is_valid = True
        token = self.request.form.get(self.widgets['dependency'].name)
        try:
            self.widgets['dependency'].vocabulary.getTermByToken(token)
        except LookupError:
            is_valid = False
        if not is_valid:
            self.setFieldError(
                'dependency',
                'There is no blueprint named "%s" in %s, or '
                '%s isn\'t valid dependency of that blueprint.' %
                (token, self.context.target.name, self.context.name))

    @action(_('Continue'), name='linkdependency')
    def linkdependency_action(self, action, data):
        self.context.createDependency(data['dependency'])

    @property
    def next_url(self):
        return canonical_url(self.context)


class SpecificationDependencyRemoveView(LaunchpadFormView):
    schema = ISpecificationDependencyRemoval
    label = 'Remove a dependency'
    field_names = ['dependency']
    for_input = True

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        self.context.removeDependency(data['dependency'])
        self.next_url = canonical_url(self.context)
