# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

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

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, IDistroRelease)

DEFAULT_LAUNCHPAD_TITLE = 'Launchpad'

# Helpers.

class BugPageTitle:
    def __call__(self, context, view):
        return "Bug #%d - %s" % (context.id, context.title)


class BugTaskPageTitle:
    def __call__(self, context, view):
        return "Bug #%d in %s - %s" % (
            context.bug.id, context.contextname, context.bug.title)


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

# Functions and strings used as the titles of pages.

attachment_index = ContextTitle('Malone Bug Attachment: %s')

attachments_index = 'Malone Bug Attachments'

bazaar_index = 'The Launchpad Bazaar'

bazaar_sync_review = 'Review upstream repositories for Launchpad Bazaar syncing'

binary_index = 'Binary Packages'

def binarypackage_index(context, view):
    return "%s binary package in Launchpad" % context.title

binarypackage_search = 'Search Binary Package Database'

binarypackagebuild_index = 'Binary Package Build Details'

binarypackagenames_index = 'Binary package name set'

binarypackagerelease_index = 'Binary Package Release Details'

binarypackagerelease_license = 'Binary Package Licence'

bounties = 'Launchpad Bounties'

bounty_subscription = 'Bounty Subscription'

bounty = ContextTitle('Launchpad Bounty: %s')

branch_index = ContextTitle('Bazaar Branch: %s')

bug_activity = ContextId('Bug #%s: Activity Log')

def bug_add(context, view):
    # XXX, Brad Bollenbach, 2005-07-15: This is a hack until our fancy
    # new page title machinery allows for two different pages that use
    # the same template to have different titles (the way ZCML does.)
    # See https://launchpad.ubuntu.com/malone/bugs/1376
    product_context = IProduct(context, None)
    distro_context = IDistribution(context, None)
    distrorelease_context = IDistroRelease(context, None)

    if product_context or distro_context or distrorelease_context is not None:
        context_title = ContextTitle('Report a bug in %s')
        return context_title(context, view)
    else:
        return "Report a bug"

bug_attachments = ContextId('Malone Bug Attachments for Bug #%s')

bug_edit = BugPageTitle()

bug_index = BugPageTitle()

bug_references = ContextId('External references for bug #%s')

bug_secrecy = ContextId('Set secrecy for bug #%s')

bug_secrecy = ContextId('Make Malone Bug #%d Public or Secret')

bugattachment_add = 'Add an Attachment'

bugwatch_editform = ContextTitle('Edit the Watch on %s')

# bugpackageinfestations_index is a redirect

# bugproductinfestations_index is a redirect

def bugs_assigned(context, view):
    if view.user:
        return 'Bugs assigned to %s' % view.user.browsername
    else:
        return 'No-one to display bugs for'

bugs_createdby_index = 'Malone Bug Report by Creator'

bugs_for_context = ContextTitle('Bugs in %s')

bugs_index = 'Malone Master Bug List'

bugsubscription_edit = 'Modify Your Bug Subscription'

bugtask_view = BugTaskPageTitle()

bugtask_edit = BugTaskPageTitle()

# bugtask_search_listing contains only macros
# bugtasks_index is a redirect

bugtracker_edit = ContextTitle('Edit %s Details')

bugtracker_index = ContextTitle('Malone Bugtracker: %s')

bugtracker_new = 'Create Malone Bugtracker'

bugtrackers_index = 'Malone-Registered Bug Trackers'

calendar = ContextTitle('%s')

calendar_event_addform = ContextTitle('Add Event to Calendar "%s"')

calendar_event_display = ContextTitle('Event "%s"')

calendar_event_editform = ContextTitle('Edit Event "%s"')

calendar_subscribe = ContextTitle('Subscribe to "%s"')

calendar_subscriptions = 'Calendar Subscriptions'

def calendar_view(context, view):
    return '%s - %s' % (context.calendar.title, view.datestring)
calendar_view_day = calendar_view
calendar_view_week = calendar_view
calendar_view_month = calendar_view
calendar_view_year = calendar_view

codeofconduct_admin = 'Administer codes of conduct in Launchpad'

codeofconduct_index = ContextTitle('%s')

codeofconduct_list = 'Codes of Conduct in Launchpad'

def cvereference_index(context, view):
    return 'Malone Bug #%s CVE Reference' % context.bug.id

# cvereferences_index is a redirect

debug_error = 'Launchpad - Error Debug Page'

debug_root_changelog = 'Launchpad Changelog'

debug_root_index = 'Launchpad Debug Home Page'

debug_unauthorized = 'Launchpad - Not Permitted'

default_addform = 'Default "Add" Page'

default_editform = 'Default "Edit" Page'

default_error = 'System Error'

distribution_cvereport = ContextTitle('CVE Reports for %s')

distribution_members = ContextTitle('%s distribution members')

distribution_memberteam = ContextTitle("Change %s's distribution team")

distribution_translators = 'Appoint Distribution Translation Group'

distro_add = 'Adding New Distribution'

distro_edit = 'Create a new Distribution in Launchpad'

distribution = ContextTitle('Launchpad Distribution Summary: %s')

# distro_sources.pt.OBSELETE
# <title metal:fill-slot="title"><span tal:replace="context/title" />: Source
# Packages</title>

distroarchrelease_index = ContextTitle('%s overview')

distroarchrelease_pkgsearch = 'Binary Package Search'

distrorelease_bugs = ContextTitle('Release %s: Bugs')

def distrorelease_deliver(context, view):
    return 'Generate ISO image for %s' % context.release.title

def distrorelease_edit(context, view):
    return 'Edit %s Details' % context.release.displayname

def distrorelease_index(context, view):
    return '%s: %s' % (context.distribution.title, context.title)

def distrorelease_new(context, view):
    return 'Create New Release of %s' % context.distribution.title

distrorelease_search = ContextDisplayName('%s Packages')

def distrorelease_sources(context, view):
    return '%s %s: Source Packages' % (
        context.release.distribution.title,
        context.release.title
        )

distrorelease_translations = ContextTitle(
    'Rosetta Translation Templates for %s')

distroreleaselanguage = ContextTitle('%s')

distros_index = 'Overview of Distributions in Launchpad'

errorservice_config = 'Configure Error Log'

errorservice_entry = 'View Error Log Report'

errorservice_index = 'View Error Log Report'

errorservice_tbentry = 'Traceback Entry'

foaf_about = 'About FOAF'

foaf_dashboard = 'Your Launchpad Dashboard'

foaf_index = 'Foaf Home Page'

foaf_mergepeople = 'Merge User Accounts'

foaf_mergerequest_sent = 'Merge User Accounts'

foaf_newaccount = 'Create a New Launchpad Account'

foaf_newteam = 'FOAF: Create a new Team'

foaf_requestmerge_multiple = 'Merge User Accounts'

foaf_requestmerge = 'Merge User Accounts'

foaf_resetpassword = 'Forgotten your Password?'

foaf_todo = 'To-Do List'

foaf_validateemail = 'Validate email address'

foaf_validateteamemail = 'Validate email address'

foaf_validategpg = 'Validate GPG Key'

karmaaction_index = 'Karma Actions'

karmaaction_edit = 'Edit Karma Action'

# launchpad_debug doesn't need a title.

def launchpad_addform(context, view):
    # Returning None results in the default Launchpad page title being used.
    return getattr(view, 'page_title', None)

launchpad_editform = launchpad_addform

launchpad_feedback = 'Help us improve Launchpad'

launchpad_forbidden = 'Forbidden'

launchpad_forgottenpassword = 'Forgot Your Launchpad Password?'

launchpad_join = 'Join the Launchpad'

# launchpad_css is a css file

# launchpad_js is standard javascript

launchpad_legal = 'Launchpad - Legalese'

launchpad_login = 'Log in or register with Launchpad'

launchpad_logout = 'Launchpad Logout'

# launchpad_widget_macros doesn't need a title.

logintoken_index = 'Launchpad: redirect to the logintoken page'

# main_template has the code to insert one of these titles.

malone_about = 'About Malone'

malone_dashboard = 'Malone Dashboard'

malone_distro_index = ContextTitle('Malone Distribution Manager: %s')

malone_distros_index = 'File a Bug in a Distribution'

malone_index = 'Malone: Collaborative Open Source Bug Management'

# malone_people_index is a redirect

# malone_template is a means to include the mainmaster template

malone_to_do = 'Malone ToDo'

milestone_add = ContextDisplayName('Add Milestone for %s')

milestone_bugs = ContextTitle('Bugs Targeted to %s')

milestone_edit = ContextTitle('Edit %s')

# messagechunk_snippet is a fragment

# messages_index is a redirect

no_app_component_yet = 'Missing App Component'

no_page_yet = 'Missing Page'

no_url_yet = 'No url for this yet'

notfound = 'Launchpad Page Not Found'

# object_pots is a fragment.

object_potemplatenames = ContextDisplayName('Template names for %s')

object_reassignment = ContextTitle('Reassign %s')

def package_bugs(context, view):
    return 'Package Bug Listing for %s' % context.name

package_search = 'Package Search'

packages_bugs = 'Packages With Bugs'

people_index = 'Launchpad People'

people_list = 'People registered with Launchpad'

person_assignedbugs = ContextDisplayName('Bugs Assigned To %s')

person_bounties = ContextDisplayName('Bounties for %s')

person_branches = ContextDisplayName("%s's code branches in Launchpad")

person_codesofconduct = ContextDisplayName('%s Signed Codes of Conduct')

person_edit = ContextDisplayName('Edit %s Information')

person_emails = ContextDisplayName('Edit %s Email Addresses')

# person_foaf is an rdf file

person_gpgkey = ContextDisplayName('%s GPG Keys')

person_index = ContextDisplayName('%s: Launchpad Overview')

person_karma = ContextDisplayName('Karma for %s')

person_key = ContextDisplayName('%s GPG Key')

person_packages = ContextDisplayName('Packages Maintained By %s')

person_reportedbugs = ContextDisplayName('Bugs Reported By %s')

person_review = ContextDisplayName("Review %s' Information")

person_sshkey = ContextDisplayName('%s SSH Keys')

person_timezone = ContextDisplayName('Time Zone for %s')

person_translations = ContextDisplayName('Translations Made By %s')

# plone.css is a css file

pofile_edit = 'Rosetta: Edit PO file details'

pofile_export = ContextTitle('%s file exports')

def pofile_index(context, view):
    return 'Rosetta: %s: %s' % (
        context.potemplate.title, context.language.englishname)

def pofile_translate(context, view):
    return 'Translating %s into %s with Rosetta' % (
        context.potemplate.displayname,
        context.language.englishname)

pofile_upload = ContextTitle('%s upload in Rosetta')

# portlet_* are portlets

poll_edit = ContextTitle('Edit poll %s')

poll_index = ContextTitle('%s')

poll_newoption = ContextTitle('Create a new Option in poll %s')

def poll_new(context, view):
    return 'Create a new Poll in team %s' % context.team.displayname

def polloption_edit(context, view):
    return 'Edit option %s' % context.shortname

potemplate_add = 'Add a new template to Rosetta'

# potemplate_chart is a fragment

potemplate_edit = ContextTitle('%s edit in Rosetta')

potemplate_index = ContextTitle('%s in Rosetta')

potemplate_upload = ContextTitle('%s upload in Rosetta')

potemplatename_add = 'Add a new template name to Rosetta'

potemplatename_edit = ContextTitle('%s edit in Rosetta')

potemplatename_index = ContextTitle('%s in Rosetta')

potemplatenames_index = 'Template names in Launchpad'

product_add = 'Register a new Product with the Launchpad'

product_bugs = ContextDisplayName('%s upstream bug reports')

product_distros = ContextDisplayName('%s packages: Comparison of distributions')

product_edit = ContextTitle('Edit Upstream Details: %s')

product_index = ContextTitle('Product: %s')

product_packages = ContextDisplayName('Packages of %s')

product_translations = ContextTitle('Rosetta Translations for %s')

def productrelease(context, view):
    return 'Details of %s %s' % (
        context.product.displayname, context.version)

def productrelease_edit(context, view):
    return 'Edit Details for %s %s' % (
        context.product.displayname, context.version)

def productrelease_new(context, view):
    return 'Register a new release of %s' % view.product.displayname

productseries_translations = ContextTitle(
    'Rosetta Translation Templates for %s')

productseries_ubuntupkg = 'Ubuntu Source Package'

products_index = 'Products in Launchpad'

products_search = 'Launchpad: Advanced Upstream Product Search'

productseries_source = 'Add Source Import'

productseries_sourceadmin = 'Add Source Import'

project = ContextTitle('Upstream Project: %s')

project_branches = ContextTitle('Bazaar Summary for %s')

project_bugs = ContextTitle('Malone Bug Summary for %s')

project_edit = ContextTitle('Edit "%s" Details')

project_index = ContextTitle('Project: %s')

project_interest = 'Rosetta: Project not translatable'

project_new = 'Register a Project with the Launchpad'

project_rosetta_index = ContextTitle('Rosetta: %s')

projects_index = 'Launchpad Project Registry'

projects_request = 'Rosetta: Request a project'

projects_search = 'Launchpad: Advanced Upstream Project Search'

# redirect_up is a redirect

def reference_index(context, view):
    return 'Web References for Malone Bug # %s' % context.bug.id

# references_index is a redirect

registry_about = 'About the Launchpad Registry'

registry_dashboard = 'Launchpad Project & Product Dashboard'

registry_index = 'Project and Product Registration in Launchpad'

registry_listall = 'Launchpad: Complete List'

registry_review = 'Launchpad Content Review'

registry_to_do = 'Launchpad To-Do List'

related_bounties = ContextDisplayName('Bounties for %s')

root_index = 'The Launchpad Home Page'

rosetta_about = 'About Rosetta'

rosetta_index = 'Rosetta'

rosetta_preferences = 'Rosetta: Preferences'

def series_edit(context, view):
    return 'Edit %s %s Details' % (context.product.displayname, context.name)

series_new = ContextDisplayName('Register a new %s release series')

def series_review(context, view):
    return 'Review %s %s Details' % (context.product.displayname, context.name)

def series(context, view):
    return '%s Release Series: %s' % (
        context.product.displayname, context.displayname)

signedcodeofconduct_index = ContextDisplayName('%s')

signedcodeofconduct_add = ContextTitle('Sign %s')

signedcodeofconduct_acknowledge = 'Acknowledge Code of Conduct Signature'

signedcodeofconduct_activate = ContextDisplayName('Activating %s')

signedcodeofconduct_deactivate = ContextDisplayName('Deactivating %s')

def sourcepackage_bugs(context, view):
    return 'Bugs in %s %s' % (
        context.distrorelease.distribution.name,
        context.sourcepackagename)

sourcepackage_buildlog = 'Source Package Build Log'

sourcepackage_changelog = 'Source Package Changelog'

sourcepackage_filebug = ContextTitle("Report a Bug in %s")

def sourcepackage_index(context, view):
    return '%s Source Packages' % context.distrorelease.title

sourcepackage = ContextTitle('%s')

sourcepackagebuild_buildlog = 'Source Package Build Log'

sourcepackagebuild_changes = 'Source Package Changes'

def sourcepackagebuild_index(context, view):
    return 'Builds: %s' % context.sourcepackagerelease.sourcepackage.summary

sourcepackagenames_index = 'Source package name set'

sourcepackagerelease_buildlog = 'Source Package Build Log'

sourcepackagerelease_index = ContextTitle('Source Package %s')

def sourcepackages(context, view):
    return '%s Source Packages' % context.distrorelease.title

sourcepackage_translations = ContextTitle(
    'Rosetta Translation Templates for %s')

sources_index = 'Bazaar: Upstream Revision Control Imports'

sourcesource_index = 'Upstream Source Import'

soyuz_about = 'About Soyuz'

soyuz_index = 'Soyuz: Linux Distribution Management'

def team_addmember(context, view):
    return '%s: Add members' % context.team.browsername

team_edit = 'Edit Team Information'

team_editemail = ContextDisplayName('Edit %s Contact Email Address')

def team_editproposed(context, view):
    return '%s Proposed Members' % context.team.browsername

team_index = ContextBrowsername('"%s" team in Launchpad')

team_join = ContextBrowsername('Join %s')

team_leave = ContextBrowsername('Leave %s')

def team_members(context, view):
    return '"%s" members' % context.team.browsername

def teammembership_index(context, view):
    return '%s: Member of %s' % (
        context.person.browsername, context.team.browsername)

team_newpoll = ContextTitle('Create a new Poll in team %s')

team_polls = ContextTitle('Polls in team %s')

template_auto_add = 'Launchpad Auto-Add Form'

template_auto_edit = 'Launchpad Auto-Edit Form'

template_edit = 'EXAMPLE EDIT TITLE'

template_index = '%EXAMPLE TITLE'

template_new = 'EXAMPLE NEW TITLE'

translationgroup = ContextTitle('Rosetta Translation Group: %s')
translationgroups = 'Rosetta Translation Groups'

ubuntite_list = 'FOAF: Ubuntite List'

# ul_main_template is probably obselete

unauthorized = 'Launchpad Permissions Notice'

user_error = 'Launchpad Error'

# watches_index is a redirect

# widget_searchselection has a commented-out title.
#     <title xmetal:fill-slot="title">Rosetta: <span
#       xtal:replace="context/title">Project Title</span></title>


