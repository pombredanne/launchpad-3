# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Browser code for the launchpad application."""

__metaclass__ = type
__all__ = [
    'AppFrontPageSearchView',
    'ApplicationButtons',
    'BrowserWindowDimensions',
    'IcingContribFolder',
    'EdubuntuIcingFolder',
    'get_launchpad_views',
    'Hierarchy',
    'IcingFolder',
    'KubuntuIcingFolder',
    'LaunchpadRootNavigation',
    'LaunchpadImageFolder',
    'LinkView',
    'LoginStatus',
    'MaintenanceMessage',
    'MaloneApplicationNavigation',
    'MaloneContextMenu',
    'MenuBox',
    'NavigationMenuTabs',
    'SoftTimeoutView',
    'StructuralHeaderPresentation',
    'StructuralObjectPresentation',
    'UbuntuIcingFolder',
    ]


import cgi
import urllib
import operator
import os
import time
from datetime import timedelta, datetime
from urlparse import urlunsplit

from zope.datetime import parseDatetimetz, tzinfo, DateTimeError
from zope.component import getUtility, queryAdapter
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest
from zope.security.interfaces import Unauthorized
from zope.traversing.interfaces import ITraversable

import canonical.launchpad.layers
from canonical.config import config
from canonical.lazr import ExportedFolder, ExportedImageFolder
from canonical.launchpad.helpers import intOrZero

from canonical.launchpad.interfaces.announcement import IAnnouncementSet
from canonical.launchpad.interfaces.binarypackagename import (
    IBinaryPackageNameSet)
from canonical.launchpad.interfaces.bounty import IBountySet
from canonical.launchpad.interfaces.branchlookup import (
    CannotHaveLinkedBranch, IBranchLookup, NoLinkedBranch)
from canonical.launchpad.interfaces.bug import IBugSet
from canonical.launchpad.interfaces.bugtracker import IBugTrackerSet
from canonical.launchpad.interfaces.builder import IBuilderSet
from canonical.launchpad.interfaces.codeimport import ICodeImportSet
from canonical.launchpad.interfaces.codeofconduct import ICodeOfConductSet
from canonical.launchpad.interfaces.cve import ICveSet
from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.interfaces.karma import IKarmaActionSet
from canonical.launchpad.interfaces.hwdb import IHWDBApplication
from canonical.launchpad.interfaces.language import ILanguageSet
from canonical.launchpad.interfaces.launchpad import (
    IAppFrontPageSearchForm, IBazaarApplication, ILaunchpadCelebrities,
    IRosettaApplication, IStructuralHeaderPresentation,
    IStructuralObjectPresentation)
from canonical.launchpad.interfaces.launchpadstatistic import (
    ILaunchpadStatisticSet)
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.interfaces.mailinglist import IMailingListSet
from canonical.launchpad.interfaces.malone import IMaloneApplication
from canonical.launchpad.interfaces.mentoringoffer import IMentoringOfferSet
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.pillar import IPillarNameSet
from canonical.launchpad.interfaces.product import IProductSet
from canonical.launchpad.interfaces.project import IProjectSet
from canonical.launchpad.interfaces.sourcepackagename import (
    ISourcePackageNameSet)
from canonical.launchpad.interfaces.specification import ISpecificationSet
from canonical.launchpad.interfaces.sprint import ISprintSet
from canonical.launchpad.interfaces.translationgroup import (
    ITranslationGroupSet)
from canonical.launchpad.interfaces.translationimportqueue import (
    ITranslationImportQueue)

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ContextMenu, Link,
    LaunchpadView, LaunchpadFormView, Navigation, stepto, canonical_name,
    canonical_url, custom_widget)
from canonical.launchpad.webapp.interfaces import (
    IBreadcrumbBuilder, ILaunchBag, ILaunchpadRoot, INavigationMenu,
    NotFoundError, POSTToNonCanonicalURL)
from canonical.launchpad.webapp.publisher import RedirectionView
from canonical.launchpad.webapp.authorization import check_permission
from lazr.uri import URI
from canonical.launchpad.webapp.url import urlparse, urlappend
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.widgets.project import ProjectScopeWidget


# XXX SteveAlexander 2005-09-22: this is imported here because there is no
#     general timedelta to duration format adapter available.  This should
#     be factored out into a generally available adapter for both this
#     code and for TALES namespace code to use.
#     Same for MenuAPI.
from canonical.launchpad.webapp.tales import DurationFormatterAPI, MenuAPI

from lp.answers.interfaces.questioncollection import IQuestionSet


class MaloneApplicationNavigation(Navigation):

    usedfor = IMaloneApplication

    newlayer = canonical.launchpad.layers.BugsLayer

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
        return getUtility(IProductSet)

    @stepto('products')
    def products(self):
        return self.redirectSubTree(
            canonical_url(getUtility(IProductSet)), status=301)

    def traverse(self, name):
        # Make /bugs/$bug.id, /bugs/$bug.name /malone/$bug.name and
        # /malone/$bug.id Just Work
        bug = getUtility(IBugSet).getByNameOrID(name)
        if not check_permission("launchpad.View", bug):
            raise Unauthorized("Bug %s is private" % name)
        return bug



class MenuBox(LaunchpadView):
    """View class that helps its template render the actions menu box.

    Nothing at all is rendered if there are no contextmenu items and also
    no applicationmenu items.

    If there is at least one item, the template is rendered.

    The context may be another view, or a content object.
    """

    def initialize(self):
        menuapi = MenuAPI(self.context)
        # We are only interested on enabled links in non development mode.
        self.contextmenuitems = sorted([
            link for link in menuapi.context.values()
            if link.enabled or config.devmode],
            key=operator.attrgetter('sort_key'))
        facet = menuapi.selectedfacetname()
        if facet not in ('unknown', 'bounties'):
            # XXX sinzui 2008-06-23 bug=242453:
            # Why are we getting unknown? Bounties are borked. We need
            # to end the facet hacks to get a clear state for the menus.
            application_links = getattr(menuapi, facet).values()
        else:
            application_links = []
        self.applicationmenuitems = sorted([
            link for link in application_links
            if link.enabled or config.devmode],
            key=operator.attrgetter('sort_key'))

    def render(self):
        if (not self.contextmenuitems and not self.applicationmenuitems):
            return u''
        else:
            return self.template()


class NavigationMenuTabs(LaunchpadView):
    """View class that helps its template render the navigation menu tabs.

    Nothing at all is rendered if there are no navigation menu items.
    """

    def initialize(self):
        menuapi = MenuAPI(self.context)
        self.links = sorted([
            link for link in menuapi.navigation.values()
            if (link.enabled or config.devmode)],
            key=operator.attrgetter('sort_key'))
        self.title = None
        if len(self.links) > 0:
            facet = menuapi.selectedfacetname()
            menu = queryAdapter(self.context, INavigationMenu, name=facet)
            if menu is not None:
                self.title = menu.title

    def render(self):
        if not self.links:
            return ''
        else:
            return self.template()


class LinkView(LaunchpadView):
    """View class that helps its template render a menu link.

    The link is not rendered if it's not enabled and we are not in development
    mode.
    """

    def render(self):
        """Render the menu link if it's enabled or we're in dev mode."""
        if self.context.enabled or config.devmode:
            # XXX: Tom Berger 2008-04-16 bug=218706:
            # We strip the result of the template rendering
            # since ZPT seems to always insert a line break
            # at the end of an embedded template.
            return self.template().strip()
        else:
            return ''


class Hierarchy(LaunchpadView):
    """The hierarchy part of the location bar on each page."""

    def items(self):
        """Return a list of `IBreadcrumb` objects visible in the hierarchy.

        The list starts with the breadcrumb closest to the hierarchy root.
        """
        urlparts = urlparse(self.request.getURL(0, path_only=False))
        baseurl = urlunsplit((urlparts[0], urlparts[1], '', '', ''))

        # Construct a list of complete URLs for each URL path segment.
        pathurls = []
        working_url = baseurl
        for segment in urlparts[2].split('/'):
            working_url = urlappend(working_url, segment)
            # Segments starting with '+' should be ignored because they
            # will never correspond to an object in navigation.
            if segment.startswith('+'):
                continue
            pathurls.append(working_url)

        # We assume a 1:1 relationship between the traversed_objects list and
        # the URL path segments.  Note that there may be more segments than
        # there are objects.
        object_urls = zip(self.request.traversed_objects, pathurls)
        return self._breadcrumbs(object_urls)

    def _breadcrumbs(self, object_urls):
        """Generate the breadcrumb list.

        :param object_urls: A sequence of (object, url) pairs.
        :return: A list of 'IBreadcrumb' objects.
        """
        breadcrumbs = []
        for obj, url in object_urls:
            crumb = self.breadcrumb_for(obj, url)
            if crumb is not None:
                breadcrumbs.append(crumb)
        return breadcrumbs

    def breadcrumb_for(self, obj, url):
        """Return the breadcrumb for the an object, using the supplied URL.

        :return: An `IBreadcrumb` object, or None if a breadcrumb adaptation
            for the object doesn't exist.
        """
        # If the object has an IBreadcrumbBuilder adaptation then the
        # object is intended to be shown in the hierarchy.
        builder = queryAdapter(obj, IBreadcrumbBuilder)
        if builder is not None:
            # The breadcrumb builder hasn't been given a URL yet.
            builder.url = url
            return builder.make_breadcrumb()
        return None

    def render(self):
        """Render the hierarchy HTML.

        The hierarchy elements are taken from the request.breadcrumbs list.
        For each element, element.text is cgi escaped.
        """
        elements = self.items()

        if config.launchpad.site_message:
            site_message = (
                '<div id="globalheader" xml:lang="en" lang="en" dir="ltr">'
                '<div class="sitemessage">%s</div></div>'
                % config.launchpad.site_message)
        else:
            site_message = ""

        if len(elements) > 0:
            # We're not on the home page.
            prefix = ('<div id="lp-hierarchy">'
                     '<span class="first-rounded"></span>')
            suffix = ('</div><span class="last-rounded">&nbsp;</span>'
                     '%s<div class="apps-separator"><!-- --></div>'
                     % site_message)

            if len(elements) == 1:
                first_class = 'before-last item'
            else:
                first_class = 'item'

            steps = []
            steps.append(
                '<span class="%s">'
                '<a href="/" class="breadcrumb container"'
                ' id="homebreadcrumb">'
                '<img alt="Launchpad"'
                ' src="/@@/launchpad-logo-and-name-hierarchy.png"/>'
                '</a>&nbsp;</span>' % first_class)

            last_element = elements[-1]
            if len(elements) > 1:
                before_last_element = elements[-2]
            else:
                before_last_element = None

            for element in elements:

                if element is before_last_element:
                    css_class = 'before-last'
                elif element is last_element:
                    css_class = 'last'
                else:
                    # No extra CSS class.
                    css_class = ''

                steps.append(
                    self.getHtmlForBreadcrumb(element, css_class))

            hierarchy = prefix + '<small> &gt; </small>'.join(steps) + suffix
        else:
            # We're on the home page.
            hierarchy = ('<div id="lp-hierarchy" class="home">'
                        '<a href="/" class="breadcrumb">'
                        '<img alt="Launchpad" '
                        ' src="/@@/launchpad-logo-and-name-hierarchy.png"/>'
                        '</a></div>'
                        '%s<div class="apps-separator"><!-- --></div>' %
                        site_message)

        return hierarchy

    def getHtmlForBreadcrumb(self, breadcrumb, extra_css_class=''):
        """Return the HTML to display an `IBreadcrumb` object.

        :param extra_css_class: A string of additional CSS classes
            to apply to the breadcrumb.
        """
        bodytext = cgi.escape(breadcrumb.text)

        if breadcrumb.icon is not None:
            bodytext = '%s %s' % (breadcrumb.icon, bodytext)

        css_class = 'item ' + extra_css_class
        return (
            '<span class="%s"><a href="%s">%s</a></span>'
            % (css_class, breadcrumb.url, bodytext))


class MaintenanceMessage:
    """Display a maintenance message if the control file is present and
    it contains a valid iso format time.

    The maintenance message shows the approximate time before launchpad will
    be taken offline for maintenance.

    The control file is +maintenancetime.txt in the launchpad root.

    If there is no maintenance message, an empty string is returned.

    If the maintenance time is too far in the future, then an empty string
    is returned.

    If the maintenance time is in the past, then the maintenance message says
    that Launchpad will go offline "very very soon".

    If the text in the maintenance message is poorly formatted, then an
    empty string is returned, and a warning should be logged.
    """

    timelefttext = None

    notmuchtime = timedelta(seconds=30)
    toomuchtime = timedelta(seconds=1800)  # 30 minutes

    def __call__(self):
        if os.path.exists('+maintenancetime.txt'):
            message = file('+maintenancetime.txt').read()
            try:
                maintenancetime = parseDatetimetz(message)
            except DateTimeError:
                # XXX SteveAlexander 2005-09-22: log a warning here.
                return ''
            nowtz = datetime.utcnow().replace(tzinfo=tzinfo(0))
            timeleft = maintenancetime - nowtz
            if timeleft > self.toomuchtime:
                return ''
            elif timeleft < self.notmuchtime:
                self.timelefttext = 'very very soon'
            else:
                self.timelefttext = 'in %s' % (
                    DurationFormatterAPI(timeleft).approximateduration())
            return self.index()
        return ''


class LaunchpadRootFacets(StandardLaunchpadFacets):

    usedfor = ILaunchpadRoot

    enable_only = ['overview', 'bugs', 'answers', 'specifications',
                   'translations', 'branches']

    def overview(self):
        target = ''
        text = 'Launchpad Home'
        return Link(target, text)

    def translations(self):
        target = ''
        text = 'Translations'
        return Link(target, text)

    def bugs(self):
        target = ''
        text = 'Bugs'
        return Link(target, text)

    def answers(self):
        target = ''
        text = 'Answers'
        summary = 'Launchpad Answer Tracker'
        return Link(target, text, summary)

    def specifications(self):
        target = ''
        text = 'Blueprints'
        summary = 'Launchpad feature specification tracker.'
        return Link(target, text, summary)

    def bounties(self):
        target = 'bounties'
        text = 'Bounties'
        summary = 'The Launchpad Universal Bounty Tracker'
        return Link(target, text, summary)

    def branches(self):
        target = ''
        text = 'Code'
        summary = 'The Code Bazaar'
        return Link(target, text, summary)


class MaloneContextMenu(ContextMenu):
    # XXX mpt 2006-03-27: No longer visible on Bugs front page.
    usedfor = IMaloneApplication
    links = ['cvetracker']

    def cvetracker(self):
        text = 'CVE tracker'
        return Link('cve/', text, icon='cve')


class LoginStatus:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

    @property
    def login_shown(self):
        return (self.user is None and
                '+login' not in self.request['PATH_INFO'])

    @property
    def logged_in(self):
        return self.user is not None

    @property
    def login_url(self):
        query_string = self.request.get('QUERY_STRING', '')

        # If we have a query string, remove some things we don't want, and
        # keep it around.
        if query_string:
            query_dict = cgi.parse_qs(query_string, keep_blank_values=True)
            query_dict.pop('loggingout', None)
            query_string = urllib.urlencode(
                sorted(query_dict.items()), doseq=True)
            # If we still have a query_string after things we don't want
            # have been removed, add it onto the url.
            if query_string:
                query_string = '?' + query_string

        # The approach we're taking is to combine the application url with
        # the path_info, taking out path steps that are to do with virtual
        # hosting.  This is not exactly correct, as the application url
        # can have other path steps in it.  We're not using the feature of
        # having other path steps in the application url, so this will work
        # for us, assuming we don't need that in the future.

        # The application_url is typically like 'http://thing:port'. No
        # trailing slash.
        application_url = self.request.getApplicationURL()

        # We're going to use PATH_INFO to remove any spurious '+index' at the
        # end of the URL.  But, PATH_INFO will contain virtual hosting
        # configuration, if there is any.
        path_info = self.request['PATH_INFO']

        # Remove any virtual hosting segments.
        path_steps = []
        in_virtual_hosting_section = False
        for step in path_info.split('/'):
            if step.startswith('++vh++'):
                in_virtual_hosting_section = True
                continue
            if step == '++':
                in_virtual_hosting_section = False
                continue
            if not in_virtual_hosting_section:
                path_steps.append(step)
        path = '/'.join(path_steps)

        # Make the URL stop at the end of path_info so that we don't get
        # spurious '+index' at the end.
        full_url = '%s%s' % (application_url, path)
        if full_url.endswith('/'):
            full_url = full_url[:-1]
        logout_url_end = '/+logout'
        if full_url.endswith(logout_url_end):
            full_url = full_url[:-len(logout_url_end)]
        return '%s/+login%s' % (full_url, query_string)


class LaunchpadRootNavigation(Navigation):

    usedfor = ILaunchpadRoot

    @stepto('support')
    def redirect_support(self):
        """Redirect /support to Answers root site."""
        target_url = canonical_url(
            getUtility(ILaunchpadRoot), rootsite='answers')
        return self.redirectSubTree(target_url + 'questions', status=301)

    @stepto('legal')
    def redirect_legal(self):
        """Redirect /legal to help.launchpad.net/Legal site."""
        return self.redirectSubTree(
            'https://help.launchpad.net/Legal', status=301)

    @stepto('faq')
    def redirect_faq(self):
        """Redirect /faq to launchpad-project/+faqs."""
        return self.redirectSubTree(
            'https://answers.launchpad.net/launchpad-project/+faqs',
            status=301)

    @stepto('feedback')
    def redirect_feedback(self):
        """Redirect /feedback to help.launchpad.net/Feedback site."""
        return self.redirectSubTree(
            'https://help.launchpad.net/Feedback', status=301)

    @stepto('+branch')
    def redirect_branch(self):
        """Redirect /+branch/<foo> to the branch named 'foo'.

        'foo' can be the unique name of the branch, or any of the aliases for
        the branch.
        """
        path = '/'.join(self.request.stepstogo)
        try:
            branch_data = getUtility(IBranchLookup).getByLPPath(path)
        except (CannotHaveLinkedBranch, NoLinkedBranch):
            raise NotFoundError
        branch, trailing = branch_data
        if branch is None:
            raise NotFoundError
        url = canonical_url(branch)
        if trailing is not None:
            url = urlappend(url, trailing)
        return self.redirectSubTree(url)

    @stepto('+builds')
    def redirect_buildfarm(self):
        """Redirect old /+builds requests to new URL, /builders."""
        new_url = '/builders'
        return self.redirectSubTree(
            urlappend(new_url, '/'.join(self.request.stepstogo)))

    # XXX cprov 2009-03-19 bug=345877: path segments starting with '+'
    # should never correspond to a valid traversal, they confuse the
    # hierarchical navigation model.
    stepto_utilities = {
        '+announcements': IAnnouncementSet,
        'binarypackagenames': IBinaryPackageNameSet,
        'bounties': IBountySet,
        'bugs': IMaloneApplication,
        'builders': IBuilderSet,
        '+code': IBazaarApplication,
        '+code-imports': ICodeImportSet,
        'codeofconduct': ICodeOfConductSet,
        'distros': IDistributionSet,
        '+hwdb': IHWDBApplication,
        'karmaaction': IKarmaActionSet,
        '+imports': ITranslationImportQueue,
        '+languages': ILanguageSet,
        '+mailinglists': IMailingListSet,
        '+mentoring': IMentoringOfferSet,
        'people': IPersonSet,
        'pillars': IPillarNameSet,
        'projects': IProductSet,
        'projectgroups': IProjectSet,
        'sourcepackagenames': ISourcePackageNameSet,
        'specs': ISpecificationSet,
        'sprints': ISprintSet,
        '+statistics': ILaunchpadStatisticSet,
        'token': ILoginTokenSet,
        '+groups': ITranslationGroupSet,
        'translations': IRosettaApplication,
        'questions': IQuestionSet,
        # These three have been renamed, and no redirects done, as the old
        # urls now point to the product pages.
        #'bazaar': IBazaarApplication,
        #'malone': IMaloneApplication,
        #'rosetta': IRosettaApplication,
        }

    @stepto('products')
    def products(self):
        return self.redirectSubTree(
            canonical_url(getUtility(IProductSet)), status=301)

    def traverse(self, name):
        if name in self.stepto_utilities:
            return getUtility(self.stepto_utilities[name])

        # Allow traversal to ~foo for People
        if name.startswith('~'):
            # account for common typing mistakes
            if canonical_name(name) != name:
                if self.request.method == 'POST':
                    raise POSTToNonCanonicalURL
                return self.redirectSubTree(
                    canonical_url(self.context) + canonical_name(name),
                    status=301)
            else:
                person = getUtility(IPersonSet).getByName(name[1:])
                # Check to see if this is a team, and if so, whether the
                # logged in user is allowed to view the team, by virtue of
                # team membership or Launchpad administration.
                if (person is None or
                    not person.is_team or
                    check_permission('launchpad.View', person)):
                    return person
                raise NotFound(self.context, name)

        # Dapper and Edgy shipped with https://launchpad.net/bazaar hard coded
        # into the Bazaar Launchpad plugin (part of Bazaar core). So in theory
        # we need to support this URL until 2011 (although I suspect the API
        # will break much sooner than that) or updates sent to
        # {dapper,edgy}-updates. Probably all irrelevant, as I suspect the
        # number of people using the plugin in edgy and dapper is 0.
        if name == 'bazaar' and IXMLRPCRequest.providedBy(self.request):
            return getUtility(IBazaarApplication)

        # account for common typing mistakes
        if canonical_name(name) != name:
            if self.request.method == 'POST':
                raise POSTToNonCanonicalURL
            return self.redirectSubTree(
                canonical_url(self.context) + canonical_name(name),
                status=301)

        pillar = getUtility(IPillarNameSet).getByName(
            name, ignore_inactive=False)
        if pillar is not None and check_permission('launchpad.View', pillar):
            if pillar.name != name:
                # This pillar was accessed through one of its aliases, so we
                # must redirect to its canonical URL.
                return self.redirectSubTree(canonical_url(pillar), status=301)
            return pillar
        return None

    def _getBetaRedirectionView(self):
        # If the inhibit_beta_redirect cookie is set, don't redirect.
        if self.request.cookies.get('inhibit_beta_redirect', '0') == '1':
            return None

        # If we are looking at the front page, don't redirect.
        if self.request['PATH_INFO'] == '/':
            return None

        # If this is a HTTP POST, we don't want to issue a redirect.
        # Doing so would go against the HTTP standard.
        if self.request.method == 'POST':
            return None

        # If no redirection host is set, don't redirect.
        mainsite_host = config.vhost.mainsite.hostname
        redirection_host = config.launchpad.beta_testers_redirection_host
        if redirection_host is None:
            return None
        # If the hostname for our URL isn't under the main site
        # (e.g. shipit.ubuntu.com), don't redirect.
        uri = URI(self.request.getURL())
        if not uri.host.endswith(mainsite_host):
            return None

        # Only redirect if the user is a member of beta testers team,
        # don't redirect.
        user = getUtility(ILaunchBag).user
        if user is None or not user.inTeam(
            getUtility(ILaunchpadCelebrities).launchpad_beta_testers):
            return None

        # Alter the host name to point at the redirection target.
        new_host = uri.host[:-len(mainsite_host)] + redirection_host
        uri = uri.replace(host=new_host)
        # Complete the URL from the environment.
        uri = uri.replace(path=self.request['PATH_INFO'])
        query_string = self.request.get('QUERY_STRING')
        if query_string:
            uri = uri.replace(query=query_string)

        # Empty the traversal stack, since we're redirecting.
        self.request.setTraversalStack([])

        # And perform a temporary redirect.
        return RedirectionView(str(uri), self.request, status=303)

    def publishTraverse(self, request, name):
        beta_redirection_view = self._getBetaRedirectionView()
        if beta_redirection_view is not None:
            return beta_redirection_view
        return Navigation.publishTraverse(self, request, name)


class SoftTimeoutView(LaunchpadView):

    def __call__(self):
        """Generate a soft timeout by sleeping enough time."""
        start_time = time.time()
        celebrities = getUtility(ILaunchpadCelebrities)
        if (self.user is None or
            not self.user.inTeam(celebrities.launchpad_developers)):
            raise Unauthorized

        self.request.response.setHeader('content-type', 'text/plain')
        soft_timeout = intOrZero(config.database.soft_request_timeout)
        if soft_timeout == 0:
            return 'No soft timeout threshold is set.'

        time.sleep(soft_timeout/1000.0)
        time_to_generate_page = (time.time() - start_time) * 1000
        # In case we didn't sleep enogh time, sleep a while longer to
        # pass the soft timeout threshold.
        while time_to_generate_page < soft_timeout:
            time.sleep(0.1)
            time_to_generate_page = (time.time() - start_time) * 1000
        return (
            'Soft timeout threshold is set to %s ms. This page took'
            ' %s ms to render.' % (soft_timeout, time_to_generate_page))


class ObjectForTemplate:

    def __init__(self, **kw):
        for name, value in kw.items():
            setattr(self, name, value)


class IcingFolder(ExportedFolder):
    """Export the Launchpad icing."""

    export_subdirectories = True

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../icing/')


class LaunchpadImageFolder(ExportedImageFolder):
    """Export the Launchpad images - supporting retrieval without extension.
    """

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../images/')


class IcingContribFolder(ExportedFolder):
    """Export the contrib icing."""

    export_subdirectories = True

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../icing-contrib/')


class UbuntuIcingFolder(ExportedFolder):
    """Export the Ubuntu icing."""

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../icing-ubuntu/')


class KubuntuIcingFolder(ExportedFolder):
    """Export the Kubuntu icing."""

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../icing-kubuntu/')


class EdubuntuIcingFolder(ExportedFolder):
    """Export the Edubuntu icing."""

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../icing-edubuntu/')



class LaunchpadTourFolder(ExportedFolder):
    """Export a launchpad tour folder.

    This exported folder supports traversing to subfolders.
    """

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../tour/')

    export_subdirectories = True

    def publishTraverse(self, request, name):
        """Hide the source directory.

        The source directory contains source material that we don't want
        published over the web.
        """
        if name == 'source':
            raise NotFound(request, name)
        return super(LaunchpadTourFolder, self).publishTraverse(request, name)

    def browserDefault(self, request):
        """Redirect to index.html if the directory itself is requested."""
        if len(self.names) == 0:
            return RedirectionView(
                "%s+tour/index" % canonical_url(self.context),
                self.request, status=302), ()
        else:
            return self, ()


class LaunchpadAPIDocFolder(ExportedFolder):
    """Export the API documentation."""

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../apidoc/')

    def browserDefault(self, request):
        """Traverse to index.html if the directory itself is requested."""
        if len(self.names) == 0:
            return self, ('index.html', )
        else:
            return self, ()


class StructuralHeaderPresentation:
    """Base class for StructuralHeaderPresentation adapters."""

    implements(IStructuralHeaderPresentation)

    def __init__(self, context):
        self.context = context

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        raise NotImplementedError()


class StructuralObjectPresentation(StructuralHeaderPresentation):
    """Base class for StructuralObjectPresentation adapters."""

    implements(IStructuralObjectPresentation)

    def listChildren(self, num):
        return []

    def countChildren(self):
        raise NotImplementedError()

    def listAltChildren(self, num):
        return None

    def countAltChildren(self):
        raise NotImplementedError()


class Button:

    def __init__(self, **kw):
        assert len(kw) == 1
        self.name = kw.keys()[0]
        self.text = kw.values()[0]
        self.replacement_dict = self.makeReplacementDict()

    def makeReplacementDict(self):
        return dict(
            url=allvhosts.configs[self.name].rooturl,
            buttonname=self.name,
            text=self.text)

    def renderActive(self):
        return (
            '<a href="%(url)s">\n'
            '  <img'
            '    width="64"'
            '    height="64"'
            '    alt="%(buttonname)s"'
            '    src="/+icing/app-%(buttonname)s-sml-active.gif"'
            '    title="%(text)s"'
            '  />\n'
            '</a>\n' % self.replacement_dict)

    def renderInactive(self):
        return (
            '<a href="%(url)s">\n'
            '  <img'
            '    width="64"'
            '    height="64"'
            '    alt="%(buttonname)s"'
            '    src="/+icing/app-%(buttonname)s-sml.gif"'
            '    title="%(text)s"'
            '  />\n'
            '</a>\n' % self.replacement_dict)

    def renderFrontPage(self):
        return (
            '<a href="%(url)s">\n'
            '  <img'
            '    width="146"'
            '    height="146"'
            '    alt="%(buttonname)s"'
            '    src="/+icing/app-%(buttonname)s.gif"'
            '    title="%(text)s"'
            '  />\n'
            '</a>\n' % self.replacement_dict)

    def renderButton(self, is_active, is_front_page):
        if (is_front_page):
            return self.renderFrontPage()
        elif is_active:
            return self.renderActive()
        else:
            return self.renderInactive()


class PeopleButton(Button):

    def makeReplacementDict(self):
        return dict(
            url='%speople/' % allvhosts.configs['mainsite'].rooturl,
            buttonname=self.name,
            text=self.text)


class ApplicationButtons(LaunchpadView):
    """Those buttons that you get on the index pages."""

    implements(ITraversable)

    def __init__(self, context, request):
        LaunchpadView.__init__(self, context, request)
        self.name = None

    buttons = [
        PeopleButton(people="Join thousands of people and teams collaborating"
            " in software development."),
        Button(code="Publish your code for people to merge and branch from."),
        Button(bugs="Share bug reports and fixes."),
        Button(blueprints="Track blueprints through approval and "
            "implementation."),
        Button(translations="Localize software into your favorite language."),
        Button(answers="Ask and answer questions about software.")
        ]

    def render(self):
        L = []
        for button in self.buttons:
            if self.name:
                is_active = button.name == self.name
            else:
                is_active = True
            is_front_page = self.name == 'main'
            L.append(button.renderButton(is_active, is_front_page))
        return u'\n'.join(L)

    def traverse(self, name, furtherPath):
        self.name = name
        if furtherPath:
            raise AssertionError(
                'Max of one path item after +applicationbuttons')
        return self


class AppFrontPageSearchView(LaunchpadFormView):

    schema = IAppFrontPageSearchForm
    custom_widget('scope', ProjectScopeWidget)

    @property
    def scope_css_class(self):
        """The CSS class for used in the scope widget."""
        if self.scope_error:
            return 'error'
        else:
            return None

    @property
    def scope_error(self):
        """The error message for the scope widget."""
        return self.getFieldError('scope')


class BrowserWindowDimensions(LaunchpadView):
    """Allow capture of browser window dimensions."""

    def render(self):
        return u'Thanks.'


def get_launchpad_views(cookies):
    """The state of optional page elements the user may choose to view.

    :param cookies: The request.cookies object that contains launchpad_views.
    :return: A dict of all the view states.
    """
    views = {
        'small_maps': True,
        }
    cookie = cookies.get('launchpad_views', '')
    if len(cookie) > 0:
        pairs = cookie.split('&')
        for pair in pairs:
            parts = pair.split('=')
            if len(parts) != 2:
                # The cookie is malformed, possibly hacked.
                continue
            key, value = parts
            if not key in views:
                # The cookie may be hacked.
                continue
            # 'false' is the value that the browser script sets to disable a
            # part of a page. Any other value is considered to be 'true'.
            views[key] = value != 'false'
    return views
