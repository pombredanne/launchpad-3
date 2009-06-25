# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Infrastructure for testing LaunchpadFormView subclasses."""

__metaclass__ = type

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from zope.security.management import (
    newInteraction, queryInteraction, endInteraction)

class LaunchpadFormHarness:

    def __init__(self, context, view_class, form_values=None):
        self.context = context
        self.view_class = view_class
        self._render(form_values)

    def _render(self, form_values=None, method='GET'):
        self.request = LaunchpadTestRequest(method=method, form=form_values,
                                            PATH_INFO='/')
        has_interaction = queryInteraction() is not None
        if not has_interaction:
            newInteraction(self.request)
        else:
            # Copy over the principal from the set-up interaction, to the
            # fake request.
            principals = [
                participation.principal
                for participation in list(queryInteraction().participations)
                if participation.principal is not None
                ]
            assert len(principals) <= 1, 'More than one principal found.'
            self.request.setPrincipal(principals[0])
        self.view = self.view_class(self.context, self.request)
        self.view.initialize()
        if not has_interaction:
            endInteraction()

    def submit(self, action_name, form_values, method='POST'):
        action_name = '%s.actions.%s' % (self.view.prefix, action_name)
        form_values = dict(form_values)
        form_values[action_name] = ''
        self._render(form_values, method)

    def hasErrors(self):
        return bool(self.view.errors)

    def getFormErrors(self):
        return self.view.form_wide_errors

    def getFieldError(self, field_name):
        return self.view.getFieldError(field_name)

    def wasRedirected(self):
        return self.request.response.getStatus() in [302, 303]

    def redirectionTarget(self):
        return self.request.response.getHeader('location')
