# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213,C0322

__metaclass__ = type
__all__ = [
    'PersonSpecWorkloadTableView',
    'PersonSpecWorkloadView',
    ]

from lp.services.propertycache import cachedproperty
from lp.services.webapp.batching import BatchNavigator
from lp.services.webapp.publisher import LaunchpadView


class PersonSpecWorkloadView(LaunchpadView):
    """View to render the specification workload for a person or team.

    It shows the set of specifications with which this person has a role.  If
    the person is a team, then all members of the team are presented using
    batching with their individual specifications.
    """

    label = 'Blueprint workload'

    @cachedproperty
    def members(self):
        """Return a batch navigator for all members.

        This batch does not test for whether the person has specifications or
        not.
        """
        members = self.context.allmembers
        batch_nav = BatchNavigator(members, self.request, size=20)
        return batch_nav

    def specifications(self):
        return self.context.specifications(self.user)


class PersonSpecWorkloadTableView(LaunchpadView):
    """View to render the specification workload table for a person.

    It shows the set of specifications with which this person has a role
    in a single table.
    """

    page_title = 'Blueprint workload'

    class PersonSpec:
        """One record from the workload list."""

        def __init__(self, spec, person):
            self.spec = spec
            self.assignee = spec.assignee == person
            self.drafter = spec.drafter == person
            self.approver = spec.approver == person

    @cachedproperty
    def workload(self):
        """This code is copied in large part from browser/sprint.py. It may
        be worthwhile refactoring this to use a common code base.

        Return a structure that lists the specs for which this person is the
        approver, the assignee or the drafter.
        """
        return [PersonSpecWorkloadTableView.PersonSpec(spec, self.context)
                for spec in self.context.specifications(self.user)]
