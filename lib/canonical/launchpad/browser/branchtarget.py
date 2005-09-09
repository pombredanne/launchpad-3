# Copyright 2005 Canonical Ltd.  All rights reserved.

"""IBranchTarget browser views."""

__metaclass__ = type

__all__ = [
    'BranchTargetView',
    ]

from canonical.launchpad.interfaces import IPerson

# XXX This stuff was cargo-culted from ITicketTarget, that needs to be factored
# out. -- David Allouche 2005-09-09


class BranchTargetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def context_relationship(self):
        url = self.request.getURL()
        if '+authoredbranches' in url:
            return "authored by"
        elif '+registeredbranches' in url:
            return "registered by"
        elif '+subscribedbranches' in url:
            return "subscribed to by"
        else:
            return "related to"

    def categories(self):
        """This organises the branches related to this target by
        "category", where a category corresponds to a particular branch
        status. It also determines the order of those categories, and the
        order of the branches inside each category. This is used for the
        +branches view.

        It is also used in IPerson, which is not an IBranchTarget but
        which does have a IPerson.branches. In this case, it will also
        detect which set of branches you want to see. The options are:

         - all branches (self.context.branches)
         - authored by this person (self.context.authored_branches)
         - registered by this person (self.context.registered_branches)
         - subscribed by this person (self.context.subscribed_branches)
        """
        categories = {}
        if not IPerson.providedBy(self.context):
            branches = self.context.branches
        else:
            url = self.request.getURL()
            if '+authoredbranches' in url:
                branches = self.context.authored_branches
            elif '+registeredbranches' in url:
                branches = self.context.registered_branches
            elif '+subscribedbranches' in url:
                branches = self.context.subscribed_branches
            else:
                branches = self.context.branches
        for branch in branches:
            if categories.has_key(branch.lifecycle_status):
                category = categories[branch.lifecycle_status]
            else:
                category = {}
                category['status'] = branch.lifecycle_status
                category['branches'] = []
                categories[branch.lifecycle_status] = category
            category['branches'].append(branch)
        categories = categories.values()
        return sorted(categories, key=lambda a: a['status'].value)
