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
    ITeamMembershipSubset, ICalendarOwner, ILanguageSet, IBugAttachmentSet,
    IPublishedPackageSet, IPollSet, IPollOptionSet, BugTaskSearchParams,
    IDistroReleaseLanguageSet)
from canonical.launchpad.database import (
    BugExternalRefSet, BugSubscriptionSet,
    BugWatchSet, BugTasksReport, CVERefSet, BugProductInfestationSet,
    BugPackageInfestationSet, ProductSeriesSet, SourcePackageSet)

def _skip_one(context, request):
    travstack = request.getTraversalStack()
    if len(travstack) == 0:
        return
    name = travstack.pop()
    request._traversed_names.append(name)
    request.setTraversalStack(travstack)
    return name

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
    elif name == "bugtrackers":
        return getUtility(IBugTrackerSet)

    return None

def traverse_potemplate(potemplate, request, name):
    user = getUtility(ILaunchBag).user
    if request.method in ['GET', 'HEAD']:
        return potemplate.getPOFileOrDummy(name, owner=user)
    elif request.method == 'POST':
        return potemplate.getOrCreatePOFile(name, owner=user)
    else:
        raise AssertionError('We only know about GET, HEAD, and POST')


def traverse_project(project, request, name):
    """Traverse an IProject."""
    if name == '+calendar':
        return ICalendarOwner(project).calendar
    else:
        try:
            return project.getProduct(name)
        except NotFoundError:
            return None


def traverse_product(product, request, name):
    """Traverse an IProduct."""
    if name == '+series':
        return ProductSeriesSet(product=product)
    elif name == '+spec':
        spec_name = _skip_one(product, request)
        return product.getSpecification(spec_name)
    elif name == '+milestone':
        milestone_name = _skip_one(product, request)
        return product.getMilestone(milestone_name)
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
                try:
                    bug = getUtility(IBugSet).get(nextstep)
                except NotFoundError:
                    return None
                return _get_task_for_context(bug, product)

    elif name == '+calendar':
        return ICalendarOwner(product).calendar
    else:
        return product.getRelease(name)

    return None


def traverse_distribution(distribution, request, name):
    """Traverse an IDistribution."""
    if name == '+packages':
        return getUtility(IPublishedPackageSet)
    elif name == '+milestone':
        milestone_name = _skip_one(distribution, request)
        return distribution.getMilestone(milestone_name)
    elif name == '+spec':
        spec_name = _skip_one(distribution, request)
        return distribution.getSpecification(spec_name)
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
                try:
                    bug = getUtility(IBugSet).get(nextstep)
                except NotFoundError:
                    return None
                return _get_task_for_context(bug, distribution)
    else:
        bag = getUtility(ILaunchBag)
        try:
            return bag.distribution[name]
        except KeyError:
            return None

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
                try:
                    bug = getUtility(IBugSet).get(nextstep)
                except NotFoundError:
                    return None
                return _get_task_for_context(bug, distrorelease)

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
        try:
            return distrorelease[name]
        except KeyError:
            return None


def _get_task_for_context(bug, context):
    user = getUtility(ILaunchBag).user
    search_params = BugTaskSearchParams(bug=bug, user=user)
    bugtasks = context.searchTasks(search_params)
    if bugtasks.count() != 1: # id not found in context. Return a 404.
        return None
    return bugtasks[0]


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
    elif name == '+poll':
        travstack = request.getTraversalStack()
        if len(travstack) == 0:
            # No option name given; returning None will raise a not found error
            return None
        # Consume the poll name from the traversal stack
        pollname = travstack.pop()
        poll = getUtility(IPollSet).getByTeamAndName(team, pollname)
        request._traversed_names.append(pollname)
        request.setTraversalStack(travstack)
        return poll

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
        return getUtility(IBugAttachmentSet)
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
    if name == '+option':
        travstack = request.getTraversalStack()
        if len(travstack) == 0:
            # No option name given; returning None will raise a not found error
            return None
        # Consume the option name from the traversal stack
        optionid = travstack.pop()
        option = getUtility(IPollOptionSet).getByPollAndId(poll, optionid)
        request._traversed_names.append(optionid)
        request.setTraversalStack(travstack)
        return option

    return None
