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

DEFAULT_LAUNCHPAD_TITLE = 'Launchpad'

# Helpers.

class SubstitutionHelper:
    def __init__(self, text):
        self.text = text

    def __call__(self, context, view):
        raise NotImplementedError


class ContextDisplayName(SubstitutionHelper):
    # XXX: salgado, 2005-06-02: This should not be used for persons because
    # they can have a NULL displayname. Maybe the right solution is to create
    # a ContextBrowserName and use it for persons.
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

auth_index = 'Launchpad Password Reminder'

bazaar_index = 'The Launchpad Bazaar'

bazaar_sync_review = 'The Bazaar Upstream-Sync Review'

binary_index = 'Binary Packages'

binarypackage_index = 'Binary Package Details'

binarypackage_search = 'Search Binary Package Database'

binarypackagebuild_index = 'Binary Package Build Details'

binarypackagenames_index = 'Binary package name set'

binarypackagerelease_index = 'Binary Package Release Details'

binarypackagerelease_license = 'Binary Package Licence'

bounties = 'Launchpad Registered Bounties'

bounty_subscription = 'Bounty Subscription'

bounty = ContextTitle('Launchpad Bounty: %s')

branch_index = ContextTitle('Bazaar Branch: %s')

bug_activity = ContextId('Activity History of Malone Bug # %s')

bug_add = 'Malone: Add a New Bug'

bug_attachments = ContextId('Malone Bug Attachments for Bug #%s')

bug_edit = ContextId('Malone: Edit Bug #%s')

bug_index = ContextId('Malone: Bug #%s')

bug_references = ContextId('External References for Malone Bug #%s')

# bugpackageinfestations_index is a redirect

# bugproductinfestations_index is a redirect

def bugs_assigned(context, view):
    return 'Malone Bugs assigned to %s' % view.user.browsername

bugs_createdby_index = 'Malone Bug Report by Creator'

bugs_index = 'Malone Master Bug List'

bugsubscription_edit = 'Modify Your Bug Subscription'

def bugtask_display(context, view):
    return 'Bug #%s in %s: %s' % (
      context.bug.id, context.contextname, context.bug.title
    )

def bugtask_editform(context, view):
    return 'Editing bug #%s in %s: %s' % (
      context.bug.id, context.contextname, context.bug.title
    )

# bugtask_search_listing contains only macros
# bugtasks_index is a redirect

bugtracker_edit = ContextTitle('Edit %s Details')

bugtracker_index = ContextTitle('Malone Bugtracker: %s')

bugtracker_new = 'Create Malone Bugtracker'

bugtrackers_index = 'Malone-Registered Bug Trackers'

codeofconduct_admin = 'Code of Conduct Admin Console'

codeofconduct_index = 'Code of Conduct Release'

codeofconduct_list = 'Launchpad Code of Conduct'

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

distribution_bugs = ContextTitle('Release %s: Bugs')

distro_add = 'Adding New Distribution'

distro_edit = 'Create a new Distribution in Launchpad'

distribution = ContextTitle('Launchpad Distribution Summary: %s')

distro_members = ContextTitle('Distribution Members: %s')

distro_search = 'Search Distributions'

# distro_sources.pt.OBSELETE
# <title metal:fill-slot="title"><span tal:replace="context/title" />: Source
# Packages</title>

def distroarchrelease_index(context, view):
    return '%s %s %s' % (
        context.distrorelease.distribution.displayname,
        context.distrorelease.displayname,
        context.title
        )

distroarchrelease_pkgsearch = 'Binary Package Search'

distrorelease_bugs = ContextTitle('Release %s: Bugs')

def distrorelease_deliver(context, view):
    return 'Generate ISO image for %s' % context.release.title

def distrorelease_edit(context, view):
    return 'Edit %s Details' % context.release.displayname

def distrorelease_index(context, view):
    return '%s: Releases' % context.distribution.title

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

distros_index = 'Overview of Distributions in Launchpad'

doap_about = 'About the Launchpad DOAP registry'

doap_dashboard = 'Launchpad Project & Product Dashboard'

doap_index = 'The DOAP Network: Project and Product Registration in Launchpad'

doap_listall = 'Launchpad: Complete List'

doap_review = 'DOAP Content Review'

doap_to_do = 'Launchpad To-Do List'

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

# launchpad_debug doesn't need a title.

def launchpad_addform(context, view):
    # Returning None results in the default Launchpad page title being used.
    return getattr(view, 'page_title', None)

launchpad_editform = launchpad_addform

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

malone_index = 'About Malone'

# malone_people_index is a redirect

# malone_template is a means to include the mainmaster template

malone_to_do = 'Malone ToDo'

# messagechunk_snippet is a fragment

# messages_index is a redirect

no_app_component_yet = 'Missing App Component'

no_page_yet = 'Missing Page'

no_url_yet = 'No url for this yet'

notfound = 'Launchpad Page Not Found'

# object_pots is a fragment.

object_potemplatenames = ContextDisplayName('Template names for %s')

def package_bugs(context, view):
    return 'Package Bug Listing for %s' % context.name

package_search = 'Package Search'

packages_bugs = 'Packages With Bugs'

people_index = 'Launchpad People'

people_list = 'People registered with Launchpad'

person_assignedbugs = ContextDisplayName('Bugs Reported By %s')

person_bounties = ContextDisplayName('Bounties for %s')

person_codesofconduct = ContextDisplayName('%s Signed Codes of Conduct')

person_edit = ContextDisplayName('Edit %s Information')

person_emails = ContextDisplayName('Edit %s Email Addresses')

# person_foaf is an rdf file

person_gpgkey = ContextDisplayName('%s GPG Keys')

person_index = ContextDisplayName('%s Personal Information')

person_karma = ContextDisplayName('Karma for %s')

person_key = ContextDisplayName('%s GPG Key')

person_packages = ContextDisplayName('Packages Maintained By %s')

person_reportedbugs = ContextDisplayName('Bugs Reported By %s')

person_sshkey = ContextDisplayName('%s SSH Keys')

person_translations = ContextDisplayName('Translations Made By %s')

# plone.css is a css file

pofile_edit = 'Rosetta: Edit PO file details'

def pofile_index(context, view):
    return 'Rosetta: %s: %s' % (
        context.potemplate.title, context.language.englishname)

def pofile_translate(context, view):
    return 'Translating %s into %s with Rosetta' % (
        context.potemplate.displayname,
        context.language.englishname)

# portlet_* are portlets

potemplage_admin = ContextTitle('%s admin in Rosetta')

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

product_edit = ContextTitle('Edit Upstream Details: %s')

product_index = ContextTitle('Product: %s')

product_translations = ContextTitle('Rosetta Translations for %s')

def productrelease(context, view):
    return 'Details of %s %s' % (
        context.product.displayname, context.version)

def productrelease_edit(context, view):
    return 'Edit Details for %s %s' % (
        context.product.displayname, context.version)

def productrelease_new(context, view):
    return 'Register a new release of %s' % view.product.displayname

productrelease_translations = ContextTitle(
    'Rosetta Translation Templates for %s')

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

related_bounties = ContextDisplayName('Bounties for %s')

root_index = 'The Launchpad Home Page'

rosetta_about = 'About Rosetta'

rosetta_index = 'Rosetta'

rosetta_preferences = 'Rosetta: Preferences'

def series_edit(context, view):
    return 'Edit %s %s Details' % (context.product.displayname, context.name)

series_new = ContextDisplayName('Register a new Release Series for %s')

def series_review(context, view):
    return 'Review %s %s Details' % (context.product.displayname, context.name)

def series(context, view):
    return '%s Release Series: %s' % (
        context.product.displayname, context.displayname)

signedcodeofconduct_index = 'Signed Code of Conduct Entry'

sourcepackage_buildlog = 'Source Package Build Log'

sourcepackage_changelog = 'Source Package Changelog'

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

team_index = ContextBrowsername('Team %s Information')

team_join = ContextBrowsername('Join %s')

team_leave = ContextBrowsername('Leave %s')

def team_members(context, view):
    return 'Members of %s' % context.team.browsername

def teammembership_index(context, view):
    return '%s: Member of %s' % (
        context.person.browsername, context.team.browsername)

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


