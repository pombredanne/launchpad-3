from zope.component import getAdapter
from canonical.launchpad.interfaces import IBugSubscriptionSet

def make_subscriptions_explicit_on_private_bug(bug, event):
    """Convert implicit subscriptions to explicit subscriptions
    when a bug is marked as privated."""
    if "private" in event.edited_fields:
        if ((not event.object_before_modification.private) and
            event.object.private):
            # the bug has been set private; turn all implicit subscriptions
            # into explicit subscriptions. basically this means explici
            subscriptions = getAdapter(bug, IBugSubscriptionSet, '')
            
            # first, add the bug submitter
            subscriptions.subscribePerson(bug.owner)

            # then add the task assignees and maintainers
            for task in bug.bugtasks:
                if task.assignee:
                    subscriptions.subscribePerson(task.assignee)
                if task.product:
                    subscriptions.subscribePerson(task.product.owner)
                else:
                    # XXX: Brad Bollenbach, 2005-02-04: I'm leaving out dealing
                    # with distro maintainers for now, because it's a rather
                    # hairy problem for the moment, perhaps best solved by
                    # abstracting into an adapter to IHasMaintainer
                    pass
