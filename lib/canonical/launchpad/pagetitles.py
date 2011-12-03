# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""*** PLEASE STOP ADDING TO THIS FILE ***

Use the page_title attribute of the view.

This module is used as a last resort by the Launchpad webapp to determine
titles for pages.

https://launchpad.canonical.com/LaunchpadTitles

** IMPORTANT ** (Brad Bollenbach, 2006-07-20) This module should not be
put in webapp, because webapp is not domain-specific, and should not be
put in browser, because this would make webapp depend on browser. SteveA
has a plan to fix this overall soon.

This module contains string or unicode literals assigned to names, or
functions such as this one:

  def bug_index(context, view):
      return 'Bug %s: %s' % (context.id, context.title)

The names of string or unicode literals and functions are the names of
the page templates, but with hyphens changed to underscores.  So, the
function bug_index given about is for the page template bug-index.pt.

If the function needs to include details from the request, this is
available from view.request.  However, these functions should not access
view.request.  Instead, the view class should make a function or
attribute available that provides the required information.

If the function returns None, it means that the default page title for
the whole of Launchpad should be used.  This is defined in the variable
DEFAULT_LAUNCHPAD_TITLE.

There are shortcuts for some common substitutions at the top of this
module.

The strings and functions for page titles are arranged in alphabetical
order after the helpers.

"""
__metaclass__ = type

from lazr.restful.utils import smartquote
from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.bugs.interfaces.malone import IMaloneApplication


DEFAULT_LAUNCHPAD_TITLE = 'Launchpad'

# Helpers.


class SubstitutionHelper:
    """An abstract class for substituting values into formatted strings."""
    def __init__(self, text):
        self.text = text

    def __call__(self, context, view):
        raise NotImplementedError


class ContextDisplayName(SubstitutionHelper):
    """Return the formatted string with context's displayname."""
    def __call__(self, context, view):
        return self.text % context.displayname


class ContextId(SubstitutionHelper):
    """Return the formatted string with context's id."""
    def __call__(self, context, view):
        return self.text % context.id


class ContextTitle(SubstitutionHelper):
    """Return the formatted string with context's title."""
    def __call__(self, context, view):
        return self.text % context.title


class LaunchbagBugID(SubstitutionHelper):
    """Return the formatted string with the bug's id from LaunchBag."""
    def __call__(self, context, view):
        return self.text % getUtility(ILaunchBag).bug.id


class ContextBugId(SubstitutionHelper):
    """Helper to include the context's bug id in the title."""

    def __call__(self, context, view):
        return self.text % context.bug.id


class ViewLabel:
    """Helper to use the view's label as the title."""
    def __call__(self, context, view):
        return view.label


def bugtarget_filebug_advanced(context, view):
    """Return the page title for reporting a bug."""
    if IMaloneApplication.providedBy(context):
        # We're generating a title for a top-level, contextless bug
        # filing page.
        return 'Report a bug'
    else:
        # We're generating a title for a contextual bug filing page.
        return 'Report a bug about %s' % context.title


bazaar_index = 'Launchpad Branches'

branch_bug_links = ContextDisplayName(smartquote('Bug links for %s'))

branch_index = ContextDisplayName(smartquote('"%s" branch in Launchpad'))


def branchmergeproposal_index(context, view):
    return 'Proposal to merge %s' % context.source_branch.bzr_identity

bug_activity = ContextBugId('Bug #%s - Activity log')

bug_addsubscriber = LaunchbagBugID("Bug #%d - Add a subscriber")

bug_branch_add = LaunchbagBugID('Bug #%d - Add branch')

bug_edit = ContextBugId('Bug #%d - Edit')

bug_mark_as_duplicate = ContextBugId('Bug #%d - Mark as duplicate')

bug_mark_as_affecting_user = ContextBugId(
    'Bug #%d - does this bug affect you?')

bug_nominate_for_series = ViewLabel()

bug_secrecy = ContextBugId('Bug #%d - Set visibility')

bug_subscription = LaunchbagBugID('Bug #%d - Subscription options')

bugbranch_delete = 'Delete bug branch link'

buglinktarget_unlinkbugs = 'Remove links to bug reports'


def buglisting_embedded_advanced_search(context, view):
    """Return the view's page heading."""
    return view.getSearchPageHeading()


def bugnomination_edit(context, view):
    """Return the title for the page to manage bug nominations."""
    return 'Manage nomination for bug #%d in %s' % (
        context.bug.id, context.target.bugtargetdisplayname)

bugtarget_bugs = ContextTitle('Bugs in %s')

bugtarget_filebug_search = bugtarget_filebug_advanced

bugtarget_filebug_submit_bug = bugtarget_filebug_advanced

bugtask_affects_new_product = LaunchbagBugID(
    'Bug #%d - Record as affecting another project')

bugtask_choose_affected_product = bugtask_affects_new_product

bugtask_confirm_bugtracker_creation = LaunchbagBugID(
    'Bug #%d - Record as affecting another software')

bugtask_requestfix = LaunchbagBugID(
    'Bug #%d - Record as affecting another distribution/package')

bugtask_requestfix_upstream = LaunchbagBugID('Bug #%d - Confirm project')

code_in_branches = 'Projects with active branches'

codeimport_list = 'Code Imports'

codeimport_machines = ViewLabel()


def codeimport_machine_index(context, view):
    return smartquote('Code Import machine "%s"' % context.hostname)

codeimport_new = ViewLabel()

cveset_all = 'All CVE entries registered in Launchpad'

cveset_index = 'Launchpad CVE tracker'

cve_index = ContextDisplayName('%s')

cve_linkbug = ContextDisplayName('Link %s to a bug report')

distribution_archive_list = ContextTitle('%s Copy Archives')

distribution_upstream_bug_report = ContextTitle('Upstream Bug Report for %s')

distribution_translations = ContextDisplayName('Translating %s')

distribution_search = ContextDisplayName(smartquote("Search %s's packages"))

distroarchseries_index = ContextTitle('%s in Launchpad')

distroarchseriesbinarypackage_index = ContextTitle('%s')

distroarchseriesbinarypackagerelease_index = ContextTitle('%s')

distroseries_translations = ContextTitle('Translations of %s in Launchpad')

distroseries_queue = ContextTitle('Queue for %s')

distroseriessourcepackagerelease_index = ContextTitle('%s')

object_templates = ContextDisplayName('Translation templates for %s')

person_translations_to_review = ContextDisplayName(
    'Translations for review by %s')

product_translations = ContextTitle('Translations of %s in Launchpad')

productseries_translations = ContextTitle('Translations overview for %s')

productseries_translations_settings = 'Settings for translations'

project_translations = ContextTitle('Translatable projects for %s')

rosetta_index = 'Launchpad Translations'

rosetta_products = 'Projects with Translations in Launchpad'
