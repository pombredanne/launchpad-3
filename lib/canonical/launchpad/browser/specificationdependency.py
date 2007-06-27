# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationDependency."""

__metaclass__ = type

__all__ = [
    'SpecificationDependencyAddView',
    'SpecificationDependencyRemoveView',
    ]

from canonical.launchpad.webapp import (
    GeneralFormView, canonical_url,
    LaunchpadFormView, action, custom_widget)
from canonical.widgets.popup import SinglePopupWidget
from canonical.launchpad.interfaces.specificationdependency import (
    ISpecificationDependency)
     
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
                    u"If another blueprint needs to be fully implemented "
                    u"before this feature can be started, then specify that "
                    u"dependency here so Launchpad knows about it and can "
                    u"give you an accurate project plan.")),
            render_context=self.render_context,
            custom_widget=self.custom_widgets['dependency'])

    @action(_('Continue'), name='linkdependency')
    def linkdependency_action(self, action, data):
        self.context.createDependency(data['dependency'])
        
    @property
    def next_url(self):
        return canonical_url(self.context)


class SpecificationDependencyRemoveView(GeneralFormView):

    def process(self, dependency):
        self._nextURL = canonical_url(self.context)
        return self.context.removeDependency(dependency)

