# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Standard browser traversal functions."""

__metaclass__ = type

__all__ = [
    'traverse_malone_application',
    'traverse_project',
    'traverse_product',
    'traverse_sourcepackage',
    'traverse_distro_sourcepackage',
    'traverse_distribution',
    'traverse_distrorelease',
    'traverse_person',
    'traverse_potemplate',
    'traverse_team',
    'traverse_bugtask',
    'traverse_bugs',
    'traverse_poll',
    ]

from zope.component import getUtility
from zope.exceptions import NotFoundError

from canonical.launchpad.interfaces import (
    IBugSet, IBugTaskSet, IDistributionSet, IProjectSet, IProductSet,
    IBugTrackerSet, ILaunchBag, ITeamMembershipSubset, ICalendarOwner,
    ILanguageSet, IBugAttachmentSet, IPublishedPackageSet, IPollSet,
    IPollOptionSet, BugTaskSearchParams, IDistroReleaseLanguageSet,
    IBugExternalRefSet, ICveSet, IBugWatchSet, IProduct,
    IDistroSourcePackageSet, ISourcePackageNameSet, IPOTemplateSet,
    IDistribution, IDistroRelease, ISourcePackage, IDistroSourcePackage)
from canonical.launchpad.database import ProductSeriesSet, SourcePackageSet
from canonical.launchpad.components.bugtask import NullBugTask

def _consume_next_path_step(request):
    """Consume the next traversal step in the request.

    This function is particularly useful if you have a URL path like:

        /foo/+things/1

    and you want the "foo" object to be the context used when rendering your ZPT
    template. Your traverser code can use this function to"consume" the +things
    path element when it traverses, so that the context remains as the "foo"
    object.

    Returns a string that is the path element that was consumed, or
    None, if there was no next path element to consume.
    """
    travstack = request.getTraversalStack()
    if len(travstack) == 0:
        return None
    name = travstack.pop()
    request._traversed_names.append(name)
    request.setTraversalStack(travstack)
    return name


def _get_task_for_context(bugid, context):
    """Return the IBugTask for this bugid in this context.

    If the bug has been reported, but not in this specific context, a
    NullBugTask will be returned.

    If no bug with the given bugid is found, None is returned.

    If the context type does provide IProduct, IDistribution,
    IDistroRelease, ISourcePackage or IDistroSourcePackage a TypeError
    is raised.
    """
    try:
        bug = getUtility(IBugSet).get(bugid)
    except NotFoundError:
        # No bug with that ID exists, so return None.
        return None

    params = BugTaskSearchParams(
        user=getUtility(ILaunchBag).user, bug=bug)
    bugtasks = context.searchTasks(params)
    if bugtasks.count():
        return bugtasks[0]
    else:
        # Return a null bug task. This makes it possible to, for
        # example, return a bug page for a context in which the bug
        # hasn't yet been reported.
        if IProduct.providedBy(context):
            null_bugtask = NullBugTask(bug=bug, product=context)
        elif IDistribution.providedBy(context):
            null_bugtask = NullBugTask(bug=bug, distribution=context)
        elif IDistroSourcePackage.providedBy(context):
            null_bugtask = NullBugTask(
                bug=bug, distribution=context.distribution,
                sourcepackagename=context.sourcepackagename)
        elif IDistroRelease.providedBy(context):
            null_bugtask = NullBugTask(bug=bug, distrorelease=context)
        elif ISourcePackage.providedBy(context):
            null_bugtask = NullBugTask(
                bug=bug, distrorelease=context.distrorelease,
                sourcepackagename=context.sourcepackagename)
        else:
            raise TypeError(
                "Unknown context type for bug task: %s" % repr(context))

        return null_bugtask


def traverse_malone_application(malone_application, request, name):
    """Traverse the Malone application object."""
    if name == "bugs":
        return getUtility(IBugSet)
    elif name == "cve":
        return getUtility(ICveSet)
    elif name == "distros":
        return getUtility(IDistributionSet)
    elif name == "projects":
        return getUtility(IProjectSet)
    elif name == "products":
        return getUtility(IProductSet)
    elif name == "bugtrackers":
        return getUtility(IBugTrackerSet)
    elif name.isdigit():
        # Make /bugs/$bug.id and /malone/$bug.id Just Work
        try:
            return getUtility(IBugSet).get(name)
        except NotFoundError:
            return None

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


def traverse_sourcepackage(sourcepackage, request, name):
    if name == '+pots':
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(
                   distrorelease=sourcepackage.distrorelease,
                   sourcepackagename=sourcepackage.sourcepackagename)
    elif name == '+bug':
        nextstep = _consume_next_path_step(request)
        if nextstep.isdigit():
            return _get_task_for_context(nextstep, sourcepackage)
        else:
            return None

    return None


def traverse_distro_sourcepackage(distro_sourcepackage, request, name):
    if name == '+bug':
        nextstep = _consume_next_path_step(request)
        if nextstep.isdigit():
            return _get_task_for_context(nextstep, distro_sourcepackage)
        else:
            return None

    return None


def traverse_product(product, request, name):
    """Traverse an IProduct."""
    if name == '+series':
        return ProductSeriesSet(product=product)
    elif name == '+spec':
        spec_name = _consume_next_path_step(request)
        return product.getSpecification(spec_name)
    elif name == '+milestone':
        milestone_name = _consume_next_path_step(request)
        return product.getMilestone(milestone_name)
    elif name == '+bug':
        nextstep = _consume_next_path_step(request)
        if nextstep.isdigit():
            return _get_task_for_context(nextstep, product)
    elif name == '+ticket':
        ticket_num = _consume_next_path_step(request)
        # tickets should be int's
        try:
            ticket_num = int(ticket_num)
        except ValueError:
            return None
        return product.getTicket(ticket_num)
    elif name == '+calendar':
        return ICalendarOwner(product).calendar
    else:
        try:
            return product.getRelease(name)
        except NotFoundError:
            return None

    return None


def traverse_distribution(distribution, request, name):
    """Traverse an IDistribution."""
    if name == '+packages':
        return getUtility(IPublishedPackageSet)
    elif name == '+sources':
        # XXX: Brad Bollenbach, 2005-09-12: There is not yet an
        # interface for $distro/+sources; for now, this code's only
        # promise is that it will return the correct
        # IDistroSourcePackage for a URL path like:
        #
        # /distros/ubuntu/+sources/mozilla-firefox
        #
        # Obviously, there needs to be a simple page designed for a
        # bare +sources. Here's the bug report to track that task:
        #
        # https://launchpad.net/malone/bugs/2230
        nextstep = _consume_next_path_step(request)
        if not nextstep:
            return None

        srcpackagename = getUtility(ISourcePackageNameSet).queryByName(nextstep)
        if not srcpackagename:
            return None

        return getUtility(IDistroSourcePackageSet).getPackage(
            distribution=distribution, sourcepackagename=srcpackagename)
    elif name == '+milestone':
        milestone_name = _consume_next_path_step(request)
        try:
            return distribution.getMilestone(milestone_name)
        except NotFoundError:
            return None
    elif name == '+spec':
        spec_name = _consume_next_path_step(request)
        return distribution.getSpecification(spec_name)
    elif name == '+ticket':
        ticket_num = _consume_next_path_step(request)
        # tickets should be int's
        try:
            ticket_num = int(ticket_num)
        except ValueError:
            return None
        return distribution.getTicket(ticket_num)
    elif name == '+bug':
        nextstep = _consume_next_path_step(request)
        if nextstep is None:
            return None
        elif nextstep.isdigit():
            return _get_task_for_context(nextstep, distribution)
        else:
            return None
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
    elif name == '+bug':
        nextstep = _consume_next_path_step(request)
        if nextstep is None:
            return None
        elif nextstep.isdigit():
            return _get_task_for_context(nextstep, distrorelease)
        else:
            return None
    else:
        try:
            return distrorelease[name]
        except KeyError:
            return None


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


def traverse_bugtask(bugtask, request, name):
    """Traverse an IBugTask."""
    utility_interface = {
        'attachments': IBugAttachmentSet,
        'references': IBugExternalRefSet,
        'watches': IBugWatchSet,
        'tasks': IBugTaskSet}

    nextstep = _consume_next_path_step(request)
    utility_iface = utility_interface.get(name)
    if utility_iface is None:
        # This is not a URL path we handle, so return None.
        return None

    utility = getUtility(utility_iface)

    if not nextstep:
        return utility

    if nextstep.isdigit():
        try:
            return utility[nextstep]
        except KeyError:
            # The object couldn't be found.
            return None

    return None


def traverse_bugs(bugcontainer, request, name):
    """Traverse an IBugSet."""
    if name == 'assigned':
        # XXX: this is obviously broken, because it's not even imported.
        #   -- kiko, 2005-09-23
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
