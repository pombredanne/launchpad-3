# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Standard browser traversal functions."""

__metaclass__ = type

__all__ = [
    'DistroReleaseNavigation',
    'ProjectNavigation',
    'SourcePackageNavigation',
    'DistroSourcePackageNavigation',
    'ProductNavigation',
    'DistributionNavigation',
    'PollNavigation',
    'BugSetNavigation',
    'MaloneApplicationNavigation',
    'TeamNavigation',
    'PersonNavigation',
    'POTemplateNavigation',
    'BugTaskNavigation',
    ]

from zope.component import getUtility, getView

from canonical.launchpad.interfaces import (
    IBugSet, IBugTask, IDistributionSet, IProjectSet, IProductSet,
    IBugTrackerSet, ILaunchBag, ITeamMembershipSubset, ICalendarOwner,
    ILanguageSet, IBugAttachmentSet, IPublishedPackageSet, IPollSet,
    IPollOptionSet, IDistroReleaseLanguageSet,
    IBugExternalRefSet, ICveSet, IBugWatchSet, IProduct, INullBugTask,
    IDistroSourcePackageSet, ISourcePackageNameSet, IPOTemplateSet,
    IDistribution, IDistroRelease, ISourcePackage, IDistroSourcePackage,
    IProject, IMaloneApplication, IPerson, ITeam, IPoll, IPOTemplate,
    NotFoundError)
from canonical.launchpad.database import ProductSeriesSet, SourcePackageSet
from canonical.launchpad.components.bugtask import NullBugTask
from canonical.launchpad.webapp import (
    Navigation, GetitemNavigation, stepthrough, redirection, stepto)
from canonical.launchpad.helpers import shortlist
import canonical.launchpad.layers


class CalendarTraversalMixin:

    @stepto('+calendar')
    def calendar(self):
        return ICalendarOwner(self.context).calendar


class BugTargetTraversalMixin:
    """Mix-in in class that provides .../+bug/NNN traversal."""

    redirection('+bug', '+bugs')

    @stepthrough('+bug')
    def traverse_bug(self, name):
        """Traverses +bug portions of URLs"""
        if name.isdigit():
            return _get_task_for_context(name, self.context)
        raise NotFoundError


class SourcePackageNavigation(Navigation, BugTargetTraversalMixin):

    usedfor = ISourcePackage

    @stepto('+pots')
    def pots(self):
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(
                   distrorelease=self.context.distrorelease,
                   sourcepackagename=self.context.sourcepackagename)


class DistroReleaseNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = IDistroRelease

    @stepthrough('+lang')
    def traverse_lang(self, langcode):
        langset = getUtility(ILanguageSet)
        try:
            lang = langset[langcode]
        except IndexError:
            # Unknown language code. Return None for a not found error
            raise NotFoundError
        drlang = self.context.getDistroReleaseLanguage(lang)
        if drlang is not None:
            return drlang
        else:
            drlangset = getUtility(IDistroReleaseLanguageSet)
            return drlangset.getDummy(self.context, lang)

    @stepto('+packages')
    def packages(self):
        return getUtility(IPublishedPackageSet)

    @stepto('+sources')
    def sources(self):
        return SourcePackageSet(distrorelease=self.context)


class ProjectNavigation(Navigation, CalendarTraversalMixin):

    usedfor = IProject

    def traverse(self, name):
        return self.context.getProduct(name)


class DistroSourcePackageNavigation(Navigation, BugTargetTraversalMixin):
    usedfor = IDistroSourcePackage


class ProductNavigation(
    Navigation, BugTargetTraversalMixin, CalendarTraversalMixin):

    usedfor = IProduct

    @stepthrough('+spec')
    def traverse_spec(self, name):
        return self.context.getSpecification(name)

    @stepto('+series')
    def series(self):
        return ProductSeriesSet(product=self.context)

    @stepthrough('+milestone')
    def traverse_milestone(self, name):
        return self.context.getMilestone(name)

    @stepthrough('+ticket')
    def traverse_ticket(self, name):
        # tickets should be ints
        try:
            ticket_num = int(name)
        except ValueError:
            raise NotFoundError
        return self.context.getTicket(ticket_num)

    def traverse(self, name):
        return self.context.getRelease(name)


def _get_task_for_context(bugid, context):
    """Return the IBugTask for this bugid in this context.

    If the bug has been reported, but not in this specific context, a
    NullBugTask will be returned.

    Raises NotFoundError if no bug with the given bugid is found.

    If the context type does provide IProduct, IDistribution,
    IDistroRelease, ISourcePackage or IDistroSourcePackage a TypeError
    is raised.
    """
    # Raises NotFoundError if no bug with that ID exists.
    bug = getUtility(IBugSet).get(bugid)

    # Loop through this bug's tasks to try and find the appropriate task for
    # this context. We always want to return a task, whether or not the user
    # has the permission to see it so that, for example, an anonymous user is
    # presented with a login screen at the correct URL, rather than making it
    # look as though this task was "not found", because it was filtered out by
    # privacy-aware code.
    for bugtask in shortlist(bug.bugtasks):
        if bugtask.target == context:
            return bugtask

    # If we've come this far, it means that no actual task exists in this
    # context, so we'll return a null bug task. This makes it possible to, for
    # example, return a bug page for a context in which the bug hasn't yet been
    # reported.
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


class MaloneApplicationNavigation(Navigation):

    usedfor = IMaloneApplication

    newlayer = canonical.launchpad.layers.MaloneLayer

    @stepto('bugs')
    def bugs(self):
        return getUtility(IBugSet)

    @stepto('bugtrackers')
    def bugtrackers(self):
        return getUtility(IBugTrackerSet)

    @stepto('cve')
    def cve(self):
        return getUtility(ICveSet)

    @stepto('distros')
    def distros(self):
        return getUtility(IDistributionSet)

    @stepto('projects')
    def projects(self):
        return getUtility(IProjectSet)

    @stepto('products')
    def products(self):
        return getUtility(IProductSet)

    def traverse(self, name):
        if name.isdigit():
            # Make /bugs/$bug.id and /malone/$bug.id Just Work
            return getUtility(IBugSet).get(name)


class POTemplateNavigation(Navigation):

    usedfor = IPOTemplate

    def traverse(self, name):
        user = getUtility(ILaunchBag).user
        if self.request.method in ['GET', 'HEAD']:
            return self.context.getPOFileOrDummy(name, owner=user)
        elif self.request.method == 'POST':
            return self.context.getOrCreatePOFile(name, owner=user)
        else:
            raise AssertionError('We only know about GET, HEAD, and POST')


class DistributionNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = IDistribution

    @stepto('+packages')
    def packages(self):
        return getUtility(IPublishedPackageSet)

    @stepthrough('+sources')
    def traverse_sources(self, name):
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
        sourcepackagenameset = getUtility(ISourcePackageNameSet)
        srcpackagename = sourcepackagenameset.queryByName(name)
        if not srcpackagename:
            raise NotFoundError
        return getUtility(IDistroSourcePackageSet).getPackage(
            distribution=self.context, sourcepackagename=srcpackagename)

    @stepthrough('+milestone')
    def traverse_milestone(self, name):
        return self.context.getMilestone(name)

    @stepthrough('+spec')
    def traverse_spec(self, name):
        return self.context.getSpecification(name)

    @stepthrough('+ticket')
    def traverse_ticket(self, name):
        # tickets should be ints
        try:
            ticket_num = int(name)
        except ValueError:
            raise NotFoundError
        return self.context.getTicket(ticket_num)


class PersonNavigation(Navigation, CalendarTraversalMixin):
    usedfor = IPerson


class TeamNavigation(Navigation, CalendarTraversalMixin):

    usedfor = ITeam

    @stepto('+members')
    def members(self):
        return ITeamMembershipSubset(self.context)

    @stepthrough('+poll')
    def traverse_poll(self, name):
        return getUtility(IPollSet).getByTeamAndName(self.context, name)


class BugTaskNavigation(Navigation):

    usedfor = IBugTask

    def traverse(self, name):
        # Are we traversing to the view or edit status page of the
        # bugtask? If so, and the task actually exists, return the
        # appropriate page. If the task doesn't yet exist (i.e. it's a
        # NullBugTask), then return a 404. In other words, the URL:
        #
        #   /products/foo/+bug/1/+viewstatus
        #
        # will return the +viewstatus page if bug 1 has actually been
        # reported in "foo". If bug 1 has not yet been reported in "foo",
        # a 404 will be returned.
        if name in ("+viewstatus", "+editstatus"):
            if INullBugTask.providedBy(self.context):
                # The bug has not been reported in this context.
                return None
            else:
                # The bug has been reported in this context.
                return getView(self.context, name + "-page", self.request)

    @stepthrough('attachments')
    def traverse_attachments(self, name):
        if name.isdigit():
            return getUtility(IBugAttachmentSet)[name]

    @stepthrough('references')
    def traverse_references(self, name):
        if name.isdigit():
            return getUtility(IBugExternalRefSet)[name]

    @stepthrough('watches')
    def traverse_watches(self, name):
        if name.isdigit():
            return getUtility(IBugWatchSet)[name]

    redirection('watches', '..')
    redirection('references', '..')


class BugSetNavigation(Navigation):

    usedfor = IBugSet

    def traverse(self, name):
        # If the bug is not found, we expect a NotFoundError. If the
        # value of name is not a value that can be used to retrieve a
        # specific bug, we expect a ValueError.
        try:
            return getUtility(IBugSet).get(name)
        except (NotFoundError, ValueError):
            return None


class PollNavigation(Navigation):

    usedfor = IPoll

    @stepthrough('+option')
    def traverse_option(self, name):
        # XXX: This code is broken, note that poll is undefined
        #   -- kiko, 2005-10-06
        return getUtility(IPollOptionSet).getByPollAndId(poll, name)

