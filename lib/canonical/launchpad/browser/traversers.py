# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Standard browser traversal functions."""

__metaclass__ = type

__all__ = [
    'traverse_malone_application',
    'traverse_project',
    'traverse_product',
    'traverse_distribution',
    'traverse_distrorelease',
    'traverse_person',
    'traverse_potemplate',
    'traverse_team',
    'traverse_bug',
    'traverse_bugs',
    'traverse_poll',
    ]

from zope.component import getUtility, queryView
from zope.exceptions import NotFoundError

from canonical.launchpad.interfaces import (
    IBugSet, IBugTaskSet, IBugTasksReport, IDistributionSet, IProjectSet,
    IProductSet, ISourcePackageSet, IBugTrackerSet, ILaunchBag,
    ITeamMembershipSubset, ICalendarOwner, ILanguageSet, IPublishedPackageSet,
    IPollSubset, IPollOptionSubset, IDistroReleaseLanguageSet)
from canonical.launchpad.database import (
    BugAttachmentSet, BugExternalRefSet, BugSubscriptionSet,
    BugWatchSet, BugTasksReport, CVERefSet, BugProductInfestationSet,
    BugPackageInfestationSet, ProductSeriesSet, ProductMilestoneSet,
    SourcePackageSet)

def traverse_malone_application(malone_application, request, name):
    """Traverse the Malone application object."""
    if name == "bugs":
        return getUtility(IBugSet)
    elif name == "assigned":
        return getUtility(IBugTasksReport)
    elif name == "distros":
        return getUtility(IDistributionSet)
    elif name == "projects":
        return getUtility(IProjectSet)
    elif name == "products":
        return getUtility(IProductSet)
    elif name == "packages":
        return getUtility(ISourcePackageSet)
    elif name == "bugtrackers":
        return getUtility(IBugTrackerSet)

    return None

def traverse_potemplate(potemplate, request, name):
    user = getUtility(ILaunchBag).user
    if request.method in ['GET', 'HEAD']:
        return potemplate.getPOFileOrDummy(name, owner=user)
    elif request.method == 'POST':
        return potemplate.getOrCreatePOFile(name, owner=user)
    raise AssertionError('We only know about GET, HEAD, and POST')


def traverse_project(project, request, name):
    """Traverse an IProject."""
    if name == '+calendar':
        return ICalendarOwner(project).calendar
    else:
        return project.getProduct(name)


def traverse_product(product, request, name):
    """Traverse an IProduct."""
    if name == '+series':
        return ProductSeriesSet(product=product)
    elif name == '+milestones':
        return ProductMilestoneSet(product=product)
    elif name == '+bugs':
        travstack = request.getTraversalStack()
        if len(travstack) == 0:
            return queryView(product, "+bugs-only", request)
        else:
            # XXX, Brad Bollenbach, 2005-07-20: This
            # request.setTraversalStack stuff is nasty. I've discussed
            # this with SteveA, and will follow his recommendation to
            # refactor this when his "nav stuff" lands.
            nextstep = travstack.pop()
            request._traversed_names.append(nextstep)
            request.setTraversalStack(travstack)

            if nextstep.isdigit():
                # This looks like a bug ID; return the task for this
                # context.
                bugtaskset = getUtility(IBugTaskSet)
                bugset = getUtility(IBugSet)

                bug = bugset.get(nextstep)
                bugtasks = bugtaskset.search(
                    product=product, bug=bug, user=getUtility(ILaunchBag).user)

                if bugtasks.count() == 1:
                    return bugtasks[0]
    elif name == '+calendar':
        return ICalendarOwner(product).calendar
    else:
        return product.getRelease(name)

    return None


def traverse_distribution(distribution, request, name):
    """Traverse an IDistribution."""
    if name == '+packages':
        return getUtility(IPublishedPackageSet)
    elif name == '+bugs':
        # XXX, Brad Bollenbach, 2005-07-20: This
        # request.setTraversalStack stuff is nasty. I've discussed
        # this with SteveA, and will follow his recommendation to
        # refactor this when his "nav stuff" lands.
        travstack = request.getTraversalStack()
        if len(travstack) == 0:
            return queryView(distribution, "+bugs-only", request)
        else:
            nextstep = travstack.pop()
            request._traversed_names.append(nextstep)
            request.setTraversalStack(travstack)

            if nextstep.isdigit():
                # This looks like a bug ID; return the task for this
                # context.
                bugtaskset = getUtility(IBugTaskSet)
                bugset = getUtility(IBugSet)

                bug = bugset.get(nextstep)
                bugtasks = bugtaskset.search(
                    distribution=distribution, bug=bug,
                    user=getUtility(ILaunchBag).user)

                if bugtasks.count() == 1:
                    return bugtasks[0]
    else:
        return getUtility(ILaunchBag).distribution[name]


def traverse_distrorelease(distrorelease, request, name):
    """Traverse an IDistroRelease."""
    if name == '+sources':
        return SourcePackageSet(distrorelease=distrorelease)
    elif name  == '+packages':
        return getUtility(IPublishedPackageSet)
    elif name == '+bugs':
        # XXX, Brad Bollenbach, 2005-07-20: This
        # request.setTraversalStack stuff is nasty. I've discussed
        # this with SteveA, and will follow his recommendation to
        # refactor this when his "nav stuff" lands.
        travstack = request.getTraversalStack()
        if len(travstack) == 0:
            return queryView(distrorelease, "+bugs-only", request)
        else:
            nextstep = travstack.pop()
            request._traversed_names.append(nextstep)
            request.setTraversalStack(travstack)

            if nextstep.isdigit():
                # This looks like a bug ID; return the task for this
                # context.
                bugtaskset = getUtility(IBugTaskSet)
                bugset = getUtility(IBugSet)

                bug = bugset.get(nextstep)
                bugtasks = bugtaskset.search(
                    distrorelease=distrorelease, bug=bug,
                    user=getUtility(ILaunchBag).user)

                if bugtasks.count() == 1:
                    return bugtasks[0]
    elif name == '+lang':
        travstack = request.getTraversalStack()
        if len(travstack) == 0:
            # no lang code passed, we return None for a not found error
            return None
        langset = getUtility(ILanguageSet)
        langcode = travstack.pop()
        request._traversed_names.append(langcode)
        try:
            lang = langset[langcode]
        except IndexError:
            # Unknown language code. Return None for a not found error
            return None
        drlang = distrorelease.getDistroReleaseLanguage(lang)
        request.setTraversalStack(travstack)
        if drlang is not None:
            return drlang
        else:
            drlangset = getUtility(IDistroReleaseLanguageSet)
            return drlangset.getDummy(distrorelease, lang)
    else:
        return distrorelease[name]


def traverse_person(person, request, name):
    """Traverse an IPerson."""
    if name == '+calendar':
        return ICalendarOwner(person).calendar

    return None


def traverse_team(team, request, name):
    if name == '+members':
        return ITeamMembershipSubset(team)
    elif name == '+calendar':
        return ICalendarOwner(team).calendar
    elif name == '+polls':
        return IPollSubset(team)

    return None


# XXX: Brad Bollenbach, 2005-06-23: From code review discussion with
# salgado, we decided it would be a good idea to turn this
# database-class using code into adapters from IBug to the appropriate
# *Set (or *Subset, perhaps.)
#
# See https://launchpad.ubuntu.com/malone/bugs/1118.
def traverse_bug(bug, request, name):
    """Traverse an IBug."""
    if name == 'attachments':
        return BugAttachmentSet(bug=bug.id)
    elif name == 'references':
        return BugExternalRefSet(bug=bug.id)
    elif name == 'cverefs':
        return CVERefSet(bug=bug.id)
    elif name == 'people':
        return BugSubscriptionSet(bug=bug.id)
    elif name == 'watches':
        return BugWatchSet(bug=bug.id)
    elif name == 'tasks':
        return getUtility(IBugTaskSet).get(bug.id)
    elif name == 'productinfestations':
        return BugProductInfestationSet(bug=bug.id)
    elif name == 'packageinfestations':
        return BugPackageInfestationSet(bug=bug.id)

    return None


def traverse_bugs(bugcontainer, request, name):
    """Traverse an IBugSet."""
    if name == 'assigned':
        return BugTasksReport()
    else:
        # If the bug is not found, we expect a NotFoundError. If the
        # value of name is not a value that can be used to retrieve a
        # specific bug, we expect a ValueError.
        try:
            return getUtility(IBugSet).get(name)
        except (NotFoundError, ValueError):
            return None


def traverse_poll(poll, request, name):
    if name == '+options':
        return IPollOptionSubset(poll)

    return None
