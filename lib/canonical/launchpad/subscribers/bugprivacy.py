from zope.component import getAdapter
from canonical.launchpad.interfaces import IBugSubscriptionSet
from canonical.launchpad.database.sourcepackage import SourcePackage

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
                    if task.sourcepackagename:
                        if task.distribution:
                            distribution = task.distribution
                        else:
                            distribution = task.distrorelease.distribution
                        # XXX: Brad Bollenbach, 2005-03-04: I'm not going
                        # to bother implementing an ISourcePackage.get,
                        # because whomever implements the
                        # Nukesourcepackage spec is going to break this
                        # code either way. Once Nukesourcepackage is
                        # implemented, the code below should be replaced
                        # with a proper implementation that uses something
                        # like an IMaintainershipSet.get
                        sourcepackages = SourcePackage.selectBy(
                            sourcepackagenameID = task.sourcepackagename.id,
                            distroID = distribution.id)
                        if sourcepackages.count():
                            subscriptions.subscribePerson(sourcepackages[0].maintainer)
