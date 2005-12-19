# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# -*- coding: utf-8 -*-

"""This module is used by the Launchpad webapp to determine titles for pages.

See https://wiki.launchpad.canonical.com/LaunchpadTitles

This module contains string or unicode literals assigned to names, or functions
such as this one:

  def bug_index(context, view):
      return 'Bug %s: %s' % (context.id, context.title)

The names of string or unicode literals and functions are the names of
the page templates, but with hyphens changed to underscores.  So, the function
bug_index given about is for the page template bug-index.pt.

If the function needs to include details from the request, this is available
from view.request.  However, these functions should not access view.request.
Instead, the view class should make a function or attribute available that
provides the required information.

If the function returns None, it means that the default page title for the
whole of Launchpad should be used.  This is defined in the variable
DEFAULT_LAUNCHPAD_TITLE.

Note that there are shortcuts for some common substitutions at the top of this
module.

The strings and functions for page titles are arranged in alphabetical order
after the helpers.

"""
__metaclass__ = type

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    IProduct, IDistribution, IDistroRelease, ILaunchBag)

DEFAULT_LAUNCHPAD_TITLE = 'Launchpad'

# Helpers.

class BugPageTitle:
    def __call__(self, context, view):
        return u"Bug #%d: “%s”" % (context.id, context.title)


class BugTaskPageTitle:
    def __call__(self, context, view):
        return u"Bug #%d in %s: “%s”" % (
            context.bug.id, context.targetname, context.bug.title)


class BugTaskTargetingTitle:
    def __call__(self, context, view):
        return "Bug #%d in %s - Target fix to releases" % (
            context.bug.id, context.targetname)


class SubstitutionHelper:
    def __init__(self, text):
        self.text = text

    def __call__(self, context, view):
        raise NotImplementedError


class ContextDisplayName(SubstitutionHelper):
    def __call__(self, context, view):
        return self.text % context.displayname


class ContextId(SubstitutionHelper):
    def __call__(self, context, view):
        return self.text % context.id


class ContextTitle(SubstitutionHelper):
    def __call__(self, context, view):
        return self.text % context.title


class ContextBrowsername(SubstitutionHelper):
    def __call__(self, context, view):
        return self.text % context.browsername


class LaunchbagBugID(SubstitutionHelper):
    def __call__(self, context, view):
        return self.text % getUtility(ILaunchBag).bug.id


# Functions and strings used as the titles of pages.

bazaar_index = 'The Launchpad Bazaar'

bazaar_sync_review = 'Review upstream repositories for Launchpad Bazaar syncing'

def binarypackagerelease_index(context, view):
    return "%s binary package in Launchpad" % context.title

binarypackagenames_index = 'Binary package name set'

bounties_index = 'Bounties registered in Launchpad'

bounty_add = 'Register a new bounty'

bounty_add = 'Register a bounty in Launchpad'

bounty_edit = ContextTitle(u'Edit bounty “%s”')

bounty_link = ContextTitle('Link a bounty to %s')

bounty_index = ContextTitle(u'Bounty “%s”')

bounty_subscription = ContextTitle(u'Subscription to bounty “%s”')

branch_edit = ContextTitle(u'Edit branch “%s”')

branch_index = ContextTitle(u'Bazaar branch “%s”')

branch_subscription = ContextTitle(u'Subscription to branch “%s”')

branchtarget_branches = ContextTitle('Branches for %s')

bug_activity = ContextId('Bug #%s - Activity log')

def bug_add(context, view):
    # XXX, Brad Bollenbach, 2005-07-15: This is a hack until our fancy
    # new page title machinery allows for two different pages that use
    # the same template to have different titles (the way ZCML does.)
    # See https://launchpad.ubuntu.com/malone/bugs/1376
    product_context = IProduct(context, None)
    distro_context = IDistribution(context, None)
    distrorelease_context = IDistroRelease(context, None)

    if product_context or distro_context or distrorelease_context is not None:
        context_title = ContextTitle('Report a bug about %s')
        return context_title(context, view)
    else:
        return "Report a bug"

bug_addsubscriber = LaunchbagBugID("Bug #%d - Add a subscriber")

bug_attachment_add = LaunchbagBugID('Bug #%d - Add an attachment')

def bug_attachment_edit(context, view):
    return u'Bug #%d - Edit attachment “%s”' % (
        context.bug.id, context.title)

bug_cve = LaunchbagBugID("Bug #%d - Add CVE reference")

bug_edit = BugPageTitle()

bug_extref_add = LaunchbagBugID("Bug #%d - Add a Web link")

def bug_extref_edit(context, view):
    return u'Bug #%d - Edit Web link “%s”' % (context.bug.id, context.title)

bug_index = BugPageTitle()

bug_mark_as_duplicate = ContextId('Bug #%d - Mark as duplicate')

bug_removecve = LaunchbagBugID("Bug #%d - Remove CVE reference")

bug_secrecy = ContextId('Bug #%d - Set visibility')

bug_subscription = ContextId('Subscription to bug #%s')

bug_watch_add = LaunchbagBugID('Bug #%d - Add external bug watch')

buglisting_advanced = ContextTitle("Bugs in %s")

buglisting_default = ContextTitle("Bugs in %s")

def bugwatch_editform(context, view):
    return 'Bug #%d - Edit external bug watch (%s in %s)' % (
        context.bug.id, context.remotebug, context.bugtracker.title)

# bugpackageinfestations_index is a redirect

# bugproductinfestations_index is a redirect

def bugs_assigned(context, view):
    if view.user:
        return 'Bugs assigned to %s' % view.user.browsername
    else:
        return 'No-one to display bugs for'

bugtask_index = BugTaskPageTitle()

bugtask_release_targeting = BugTaskTargetingTitle()

bugtask_view = BugTaskPageTitle()

bugtask_edit = BugTaskPageTitle()

# bugtask_macros_buglisting contains only macros
# bugtasks_index is a redirect

bugtracker_edit = ContextTitle(u'Edit bug tracker “%s”')

bugtracker_index = ContextTitle(u'Bug tracker “%s”')

bugtrackers_add = 'Register a bug tracker in Malone'

bugtrackers_index = 'Bug trackers registered in Malone'

build_buildlog = ContextTitle('Build log for %s')

build_changes = ContextTitle('Changes in %s')

build_index = ContextTitle('Build details for %s')

builders = 'Launchpad build farm'

builder_edit = ContextTitle(u'Edit build machine “%s”')

builder_index = ContextTitle(u'Build machine “%s”')

builder_cancel = ContextTitle(u'Cancel job for “%s”')

builder_mode = ContextTitle('Change mode for “%s”')

calendar_index = ContextTitle('%s')

calendar_event_addform = ContextTitle(u'Add event to %s')

calendar_event_display = ContextTitle(u'Event “%s”')

calendar_event_editform = ContextTitle(u'Edit event “%s”')

calendar_subscribe = ContextTitle(u'Subscribe to “%s”')

calendar_subscriptions = 'Calendar subscriptions'

def calendar_view(context, view):
    return '%s - %s' % (context.calendar.title, view.datestring)
calendar_view_day = calendar_view
calendar_view_week = calendar_view
calendar_view_month = calendar_view
calendar_view_year = calendar_view

codeofconduct_admin = 'Administer codes of conduct in Launchpad'

codeofconduct_index = ContextTitle('%s')

codeofconduct_list = 'Codes of conduct in Launchpad'

cveset_all = 'All CVE entries registered in Launchpad'

cveset_index = 'Launchpad CVE tracker'

cve_index = ContextDisplayName('%s')

cve_bug = ContextDisplayName('Link %s to a bug report')

cve_removebug = ContextDisplayName('Remove link between %s and a bug report')

debug_root_changelog = 'Launchpad changelog'

debug_root_index = 'Launchpad Debug Home Page'

default_editform = 'Default "Edit" Page'

distribution_allpackages = ContextTitle('All packages in %s')

distribution_cvereport = ContextTitle('CVE reports for %s')

distribution_members = ContextTitle('%s distribution members')

distribution_memberteam = ContextTitle(u'Change %s’s distribution team')

distribution_translations = ContextDisplayName('Translating %s')

distribution_translators = ContextTitle(u'Appoint %s’s translation group')

distribution_search = ContextDisplayName(u'Search %s’s packages')

distribution_index = ContextTitle('%s in Launchpad')

distribution_builds = ContextTitle('%s builds')

distributionsourcepackage_bugs = ContextTitle('Bugs in %s')

distributionsourcepackage_index = ContextTitle('%s')

distributionsourcepackagerelease_index = ContextTitle('%s')

distroarchrelease_admin = ContextTitle('Administer %s')

distroarchrelease_index = ContextTitle('%s in Launchpad')

distroarchrelease_builds = ContextTitle('%s builds')

distroarchrelease_search = ContextTitle(u'Search %s’s binary packages')

distroarchreleasebinarypackage_index = ContextTitle('%s')

distroarchreleasebinarypackagerelease_index = ContextTitle('%s')

distrorelease_addport = ContextTitle('Add a port of %s')

distrorelease_bugs = ContextTitle('Bugs in %s')

distrorelease_cvereport = ContextDisplayName('CVE report for %s')

def distrorelease_index(context, view):
    return '%s %s in Launchpad' % (context.distribution.title, context.version)

distrorelease_packaging = ContextDisplayName('Mapping packages to upstream '
    'for %s')

distrorelease_search = ContextDisplayName('Search packages in %s')

distrorelease_translations = ContextTitle('Translations of %s in Rosetta')

distrorelease_builds = ContextTitle('Builds for %s')

distroreleasebinarypackage_index = ContextTitle('%s')

distroreleaselanguage = ContextTitle('%s')

distroreleasesourcepackagerelease_index = ContextTitle('%s')

distros_index = 'Distributions registered in Launchpad'

errorservice_config = 'Configure error log'

errorservice_entry = 'Error log entry'

errorservice_index = 'Error log report'

errorservice_tbentry = 'Traceback entry'

foaf_mergepeople = 'Merge accounts'
# XXX mpt 20051209: Include the account you're merging in the title

foaf_mergerequest_sent = 'Merge request sent'

foaf_newaccount = 'Get a Launchpad account'

foaf_newteam = 'Register a new team in Launchpad'

foaf_requestmerge_multiple = 'Merge Launchpad accounts'

foaf_requestmerge = 'Merge Launchpad accounts'

foaf_resetpassword = 'Reset your Launchpad password'

foaf_validateemail = 'Confirm e-mail address'

foaf_validateteamemail = 'Confirm e-mail address'

foaf_validategpg = 'Confirm OpenPGP key'

foaf_validatesignonlygpg = 'Confirm sign-only OpenPGP key'

karmaaction_index = 'Karma actions'

karmaaction_edit = 'Edit karma action'

# launchpad_debug doesn't need a title.

def launchpad_addform(context, view):
    # Returning None results in the default Launchpad page title being used.
    return getattr(view, 'page_title', None)

launchpad_editform = launchpad_addform

launchpad_feedback = 'Help us improve Launchpad'

launchpad_forbidden = 'Forbidden'

launchpad_forgottenpassword = 'Forgotten your Launchpad password?'

template_form = 'XXX PLEASE DO NOT USE THIS TEMPLATE XXX'

# launchpad_css is a css file

# launchpad_js is standard javascript

# XXX: The general form is a fallback form; I'm not sure why it is
# needed, nor why it needs a pagetitle, but I can't debug this today.
#   -- kiko, 2005-09-29
launchpad_generalform = "Launchpad - General Form (Should Not Be Displayed)"

launchpad_legal = 'Launchpad legalese'

launchpad_login = 'Log in or register with Launchpad'

launchpad_log_out = 'Log out from Launchpad'

launchpad_notfound = 'Error: Page not found'

launchpad_oops = 'Error: Oops'

launchpad_requestexpired = 'Error: Timeout'

# launchpad_widget_macros doesn't need a title.

logintoken_index = 'Launchpad: redirect to the logintoken page'

# main_template has the code to insert one of these titles.

malone_about = 'About Malone'

malone_distros_index = 'Report a bug about a distribution'

malone_index = 'Malone: the Launchpad bug tracker'

# malone_people_index is a redirect

# malone_template is a means to include the mainmaster template

# messagechunk_snippet is a fragment

# messages_index is a redirect

message_add = ContextId('Bug #%d - Add a comment')

milestone_add = ContextDisplayName('Add milestone for %s')

milestone_index = ContextTitle('%s')

milestone_edit = ContextTitle('Edit %s')

no_app_component_yet = 'Missing App Component'

no_page_yet = 'Missing Page'

no_url_yet = 'No url for this yet'

# object_pots is a fragment.

object_potemplatenames = ContextDisplayName('Template names for %s')

object_reassignment = ContextTitle('Reassign %s')

def package_bugs(context, view):
    return 'Bugs in %s' % context.name

people_index = 'People registered with Launchpad'

people_list = 'People registered with Launchpad'

person_assignedbugs = ContextDisplayName('Bugs assigned to %s')

person_bounties = ContextDisplayName('Bounties for %s')

person_branch_add = ContextDisplayName('Register a new branch for %s')

person_changepassword = 'Change your password'

person_codesofconduct = ContextDisplayName('%s Signed codes of conduct')

person_edit = ContextDisplayName(u'%s’s details')

person_editemails = ContextDisplayName(u'%s’s e-mail addresses')

person_editgpgkeys = ContextDisplayName(u'%s’s OpenPGP keys')

person_edithomepage = ContextDisplayName(u'%s’s home page')

person_editircnicknames = ContextDisplayName(u'%s’s IRC nicknames')

person_editjabberids = ContextDisplayName(u'%s’s Jabber IDs')

person_editsshkeys = ContextDisplayName(u'%s’s SSH keys')

person_editwikinames = ContextDisplayName(u'%s’s wiki names')

# person_foaf is an rdf file

person_images = ContextDisplayName(u'%s’s hackergotchi and emblem')

person_index = ContextDisplayName('%s in Launchpad')

person_karma = ContextDisplayName(u'%s’s karma in Launchpad')

person_packages = ContextDisplayName('Packages maintained by %s')

person_packagebugs = ContextDisplayName('Bugs on software %s maintains')

person_reportedbugs = ContextDisplayName('Bugs %s reported')

person_review = ContextDisplayName("Review %s")

person_subscribedbugs = ContextDisplayName('Bugs %s is subscribed to')

person_translations = ContextDisplayName('Translations made by %s')

person_teamhierarchy = ContextDisplayName('Team hierarchy for %s')

pofile_edit = 'Rosetta: Edit PO file details'
# XXX mpt 20051209: This should be more context-sensitive

pofile_export = ContextTitle('%s file exports')

def pofile_index(context, view):
    return 'Rosetta: %s in %s' % (
        context.potemplate.title, context.language.englishname)

def pofile_translate(context, view):
    return 'Translating %s into %s with Rosetta' % (
        context.potemplate.displayname,
        context.language.englishname)

pofile_upload = ContextTitle('%s upload in Rosetta')

# portlet_* are portlets

poll_edit = ContextTitle(u'Edit poll “%s”')

poll_index = ContextTitle(u'Poll: “%s”')

poll_newoption = ContextTitle(u'New option for poll “%s”')

def poll_new(context, view):
    return 'Create a new Poll in team %s' % context.team.displayname

def polloption_edit(context, view):
    return 'Edit option: %s' % context.title

poll_options = ContextTitle(u'Options for poll “%s”')

poll_vote_condorcet = ContextTitle(u'Vote in poll “%s”')

poll_vote_simple = ContextTitle(u'Vote in poll “%s”')

potemplate_add = 'Add a new template to Rosetta'

# potemplate_chart is a fragment

potemplate_edit = ContextTitle(u'Edit “%s” in Rosetta')

potemplate_index = ContextTitle(u'“%s” in Rosetta')

potemplate_upload = ContextTitle(u'“%s” upload in Rosetta')

potemplate_export = ContextTitle(u'Export translations of “%s”')

potemplatename_add = 'Add a new template name to Rosetta'

potemplatename_edit = ContextTitle(u'Edit “%s” in Rosetta')

potemplatename_index = ContextTitle(u'“%s” in Rosetta')

potemplatenames_index = 'Template names in Launchpad'

product_add = 'Register a product with Launchpad'

product_bugs = ContextDisplayName('Bugs in %s')

product_branches = ContextDisplayName(u'%s’s code branches in Launchpad')

product_distros = ContextDisplayName('%s packages: Comparison of distributions')

product_edit = ContextTitle('%s in Launchpad')

product_index = ContextTitle('%s in Launchpad')

product_packages = ContextDisplayName('%s packages in Launchpad')

product_translations = ContextTitle(u'Translations of %s in Rosetta')

def productrelease(context, view):
    return '%s %s in Launchpad' % (
        context.product.displayname, context.version)

def productrelease_edit(context, view):
    return '%s %s in Launchpad' % (
        context.product.displayname, context.version)

productrelease_add = ContextTitle('Register a new %s release in Launchpad')

productseries_translations = ContextTitle('Translation templates for %s')

productseries_ubuntupkg = 'Ubuntu source package'

products_index = 'Products registered in Launchpad'

productseries_source = 'Import product series'

productseries_sourceadmin = 'Add source import'

project = ContextTitle('%s in Launchpad')

project_branches = ContextTitle('Bazaar branches for %s')

project_bugs = ContextTitle('Bugs in %s')

project_edit = ContextTitle('%s project details')

project_interest = 'Rosetta: Project not translatable'

project_rosetta_index = ContextTitle('Rosetta: %s')

projects_index = 'Projects registered in Launchpad'

projects_request = 'Rosetta: Request a project'

projects_search = 'Search for projects in Launchpad'

rdf_index = "Launchpad RDF"

# redirect_up is a redirect

def reference_index(context, view):
    return 'Web links for bug %s' % context.bug.id

# references_index is a redirect

registry_about = 'About the Launchpad Registry'

registry_index = 'Product and group registration in Launchpad'

registry_listall = 'Launchpad: Complete list' # bug 3508

registry_review = 'Review Launchpad items'

related_bounties = ContextDisplayName('Bounties for %s')

root_index = 'Launchpad'

rosetta_about = 'About Rosetta'

rosetta_index = 'Rosetta'

rosetta_preferences = 'Rosetta: Preferences'

product_branch_add = ContextDisplayName('Register a new %s branch')

def productseries_edit(context, view):
    return '%s %s details' % (context.product.displayname, context.name)

productseries_new = ContextDisplayName('Register a new %s release series')

def productseries(context, view):
    return '%s release series: %s' % (
        context.product.displayname, context.displayname)

shipit_index = 'ShipIt'

shipit_exports = 'ShipIt exports'

shipit_myrequest = "Your ShipIt order"

shipit_reports = 'ShipIt reports'

shipitrequests_index = 'ShipIt requests'

shipitrequests_search = 'Search ShipIt requests'

shipitrequest_edit = 'Edit ShipIt request'

shipit_notfound = 'Error: Page not found'

shipit_default_error = 'Error: Oops'

signedcodeofconduct_index = ContextDisplayName('%s')

signedcodeofconduct_add = ContextTitle('Sign %s')

signedcodeofconduct_acknowledge = 'Acknowledge code of conduct signature'

signedcodeofconduct_activate = ContextDisplayName('Activating %s')

signedcodeofconduct_deactivate = ContextDisplayName('Deactivating %s')

sourcepackage = ContextTitle('%s')

sourcepackage_bugs = ContextDisplayName('Bugs in %s')

sourcepackage_buildlog = ContextTitle('Build log for %s')

sourcepackage_builds = ContextTitle('Builds for %s')

sourcepackage_translate = ContextTitle('Help translate %s')

sourcepackage_changelog = 'Source package changelog'

sourcepackage_filebug = ContextTitle("Report a bug about %s")

sourcepackage_gethelp = ContextTitle('Help and support options for %s')

sourcepackage_hctstatus = ContextTitle('%s HCT status')

def sourcepackage_index(context, view):
    return '%s source packages' % context.distrorelease.title

sourcepackage_packaging = ContextTitle('Define upstream series for %s')

sourcepackage_translate = ContextTitle('Help translate %s')

sourcepackage_translations = ContextTitle(
    'Rosetta translation templates for %s')

sourcepackagebuild_buildlog = 'Source package build log'

sourcepackagebuild_changes = 'Source package changes'

def sourcepackagebuild_index(context, view):
    return 'Builds of %s' % context.sourcepackagerelease.sourcepackage.summary

sourcepackagenames_index = 'Source package name set'

sourcepackagerelease_index = ContextTitle('Source package %s')

def sourcepackages(context, view):
    return '%s source packages' % context.distrorelease.title

sourcepackages_comingsoon = 'Coming soon'

sources_index = 'Bazaar: Upstream revision control imports'

sourcesource_index = 'Upstream source import'

specification_add = 'Register a feature specification in Launchpad'

specification_addsubscriber = 'Subscribe someone else to this spec'

specification_bug = ContextTitle(
  'Link specification \N{left double quotation mark}%s'
  '\N{right double quotation mark} to a bug report')

specification_removebug = 'Remove link to bug report'

specification_retargeting = 'Attach spec to a different product or distribution'

specification_superseding = 'Mark specification as superseded by another'

specification_dependency = 'Create a specification dependency'

specification_deptree = 'Complete dependency tree'

specification_milestone = 'Target feature to milestone'

specification_people = 'Change specification assignee, drafter, and reviewer'

specification_priority = 'Change specification priority'

specification_distrorelease = ('Target specification at a distribution release')

specification_productseries = 'Target specification at a series'

specification_removedep = 'Remove a dependency'

specification_givefeedback = 'Clear feedback requests'

specification_requestfeedback = 'Request feedback on this specification'

specification_edit = 'Edit specification details'

specification_linksprint = 'Put specification on sprint agenda'

specification_status = 'Edit specification status'

specification_index = ContextTitle(u'Feature specification: “%s”')

specification_subscription = 'Subscribe to specification'

specification_queue = 'Queue specification for review'

specifications_index = ContextTitle('%s')

specificationtarget_specs = ContextTitle('Specifications for %s')

specificationtarget_specplan = ContextTitle('Project plan for %s')

specificationtarget_workload = ContextTitle('Feature workload in %s')

sprint_attend = ContextTitle('Register your attendance at %s')

sprint_edit = ContextTitle(u'Edit “%s” details')

sprint_index = ContextTitle('%s (sprint or meeting)')

sprint_new = 'Register a meeting or sprint in Launchpad'

sprint_register = 'Register someone to attend this meeting'

sprint_table = ContextTitle('Table of specifications for %s')

sprint_workload = ContextTitle('Workload at %s')

sprints_index = 'Meetings and sprints registered in Launchpad'

sprintspecification_edit = 'Edit specification-sprint relationship'

sprintspecification_admin = 'Approve specification for sprint agenda'

tickets_index = 'Launchpad tech support system'

ticket_add = ContextDisplayName('Request support with %s')

ticket_bug = ContextId(u'Link support request #%s to a bug report')

ticket_edit = ContextId('Edit support request #%s details')

def ticket_index(context, view):
    text = (
        u'%s support request #%d: “%s”' %
        (context.target.displayname, context.id, context.title))
    return text

ticket_history = ContextId('History of support request #%s')

ticket_makebug = ContextId('Create bug report based on request #%s')

ticket_reject = ContextId('Reject support request #%s')

ticket_removebug = ContextId('Remove bug link from request #%s')

ticket_reopen = ContextId('Reopen request #%s')

ticket_subscription = ContextId('Subscription to request #%s')

tickettarget_tickets = ContextTitle('Support requests for %s')

standardshipitrequests_index = 'Standard ShipIt options'

standardshipitrequest_new = 'Create a new standard option'

standardshipitrequest_edit = 'Edit standard option'

team_addmember = ContextBrowsername('Add members to %s')

team_edit = 'Edit team information'

team_editemail = ContextDisplayName('%s contact e-mail address')

team_index = ContextBrowsername(u'“%s” team in Launchpad')

team_editproposed = ContextBrowsername('Proposed members of %s')

team_join = ContextBrowsername('Join %s')

team_leave = ContextBrowsername('Leave %s')

team_members = ContextBrowsername(u'“%s” members')

def teammembership_index(context, view):
    return u'%s’s membership status in %s' % (
        context.person.browsername, context.team.browsername)

team_newpoll = ContextTitle('New poll for team %s')

team_polls = ContextTitle('Polls for team %s')

template_auto_add = 'Launchpad Auto-Add Form'

template_auto_edit = 'Launchpad Auto-Edit Form'

template_edit = 'EXAMPLE EDIT TITLE'

template_index = '%EXAMPLE TITLE'

template_new = 'EXAMPLE NEW TITLE'

translationgroup = ContextTitle(u'“%s” Rosetta translation group')

translationgroups = 'Rosetta translation groups'

unauthorized = 'Error: Not authorized'
