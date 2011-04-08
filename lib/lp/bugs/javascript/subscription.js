/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide information and actions on all bug subscriptions a person holds.
 *
 * @module bugs
 * @submodule subscription
 */

YUI.add('lp.bugs.subscription', function(Y) {

var namespace = Y.namespace('lp.bugs.subscription');

/**
 * These are the descriptions strings of what might be the cause of you
 * getting an email.
 */

var _BECAUSE_YOU_ARE = 'You receive emails about this bug because you are ';

/* These are components for team participation. */
var _OF_TEAM = 'of the team {team}. That team is ';
var _OF_TEAMS = 'of the teams {teams}.  Those teams are ';
var _BECAUSE_TEAM_IS = _BECAUSE_YOU_ARE + 'a member ' + _OF_TEAM;
var _ADMIN_BECAUSE_TEAM_IS = (
    _BECAUSE_YOU_ARE + 'a member and administrator ' + _OF_TEAM);
var _BECAUSE_TEAMS_ARE = _BECAUSE_YOU_ARE + 'a member ' + _OF_TEAMS;
var _ADMIN_BECAUSE_TEAMS_ARE = (
        _BECAUSE_YOU_ARE + 'a member and administrator ' + _OF_TEAMS);

/* These are the assignment variations. */
var _ASSIGNED = 'assigned to work on it.';
/* These are the actual strings to use. */
var YOU_ASSIGNED = _BECAUSE_YOU_ARE + _ASSIGNED;
var TEAM_ASSIGNED = _BECAUSE_TEAM_IS + _ASSIGNED;
var ADMIN_TEAM_ASSIGNED = _ADMIN_BECAUSE_TEAM_IS + _ASSIGNED;
var TEAMS_ASSIGNED = _BECAUSE_TEAMS_ARE + _ASSIGNED;
var ADMIN_TEAMS_ASSIGNED = _ADMIN_BECAUSE_TEAMS_ARE + _ASSIGNED;

/* These are the direct subscription variations. */
var _SUBSCRIBED = 'directly subscribed to it.';
var _MAY_HAVE_BEEN_CREATED = ' This subscription may have been created ';
/* Now these are the actual options we use. */
var YOU_SUBSCRIBED = _BECAUSE_YOU_ARE + _SUBSCRIBED;
var YOU_REPORTED = (YOU_SUBSCRIBED + _MAY_HAVE_BEEN_CREATED +
                    'when you reported the bug.');
var YOU_SUBSCRIBED_BUG_SUPERVISOR = (
    YOU_SUBSCRIBED + _MAY_HAVE_BEEN_CREATED +
        'because the bug was private and you are a bug supervisor.');
var YOU_SUBSCRIBED_SECURITY_CONTACT = (
    YOU_SUBSCRIBED + _MAY_HAVE_BEEN_CREATED +
        'because the bug was security related and you are ' +
        'a security contact.');
var TEAM_SUBSCRIBED = _BECAUSE_TEAM_IS + _SUBSCRIBED;
var ADMIN_TEAM_SUBSCRIBED = _ADMIN_BECAUSE_TEAM_IS + _SUBSCRIBED;
var TEAMS_SUBSCRIBED = _BECAUSE_TEAMS_ARE + _SUBSCRIBED;
var ADMIN_TEAMS_SUBSCRIBED = _ADMIN_BECAUSE_TEAMS_ARE + _SUBSCRIBED;

/* These are the duplicate bug variations. */
var _SUBSCRIBED_TO_DUPLICATE = (
    'a direct subscriber to bug {dupe_bug_id}, which is marked as a ' +
        'duplicate of this bug, {bug_id}');
var _SUBSCRIBED_PLURAL_TO_DUPLICATE = (
    'direct subscribers to bug {dupe_bug_id}, which is marked as a ' +
        'duplicate of this bug, {bug_id}');
var _SUBSCRIBED_TO_DUPLICATES = (
    'a direct subscriber to bugs {dupe_bug_ids}, which are marked as ' +
        'duplicates of this bug, {bug_id}');
var _SUBSCRIBED_PLURAL_TO_DUPLICATES = (
    'direct subscribers to bugs {dupe_bug_ids}, which are marked as ' +
        'duplicates of this bug, {bug_id}');
/* These are the actual strings to use. */
var YOU_SUBSCRIBED_TO_DUPLICATE = _BECAUSE_YOU_ARE + _SUBSCRIBED_TO_DUPLICATE;
var YOU_SUBSCRIBED_TO_DUPLICATES = (
    _BECAUSE_YOU_ARE + _SUBSCRIBED_TO_DUPLICATES);
var TEAM_SUBSCRIBED_TO_DUPLICATE = _BECAUSE_TEAM_IS + _SUBSCRIBED_TO_DUPLICATE;
var TEAM_SUBSCRIBED_TO_DUPLICATES = (
    _BECAUSE_TEAM_IS + _SUBSCRIBED_TO_DUPLICATES);
var ADMIN_TEAM_SUBSCRIBED_TO_DUPLICATE = (
    _ADMIN_BECAUSE_TEAM_IS + _SUBSCRIBED_TO_DUPLICATE);
var ADMIN_TEAM_SUBSCRIBED_TO_DUPLICATES = (
    _ADMIN_BECAUSE_TEAM_IS + _SUBSCRIBED_TO_DUPLICATES);
var TEAMS_SUBSCRIBED_TO_DUPLICATE = (
    _BECAUSE_TEAMS_ARE + _SUBSCRIBED_PLURAL_TO_DUPLICATE);
var TEAMS_SUBSCRIBED_TO_DUPLICATES = (
    _BECAUSE_TEAMS_ARE + _SUBSCRIBED_PLURAL_TO_DUPLICATES);
var ADMIN_TEAMS_SUBSCRIBED_TO_DUPLICATE = (
    _ADMIN_BECAUSE_TEAMS_ARE + _SUBSCRIBED_PLURAL_TO_DUPLICATE);
var ADMIN_TEAMS_SUBSCRIBED_TO_DUPLICATES = (
    _ADMIN_BECAUSE_TEAMS_ARE + _SUBSCRIBED_PLURAL_TO_DUPLICATES);

// XXX You don't get email for duplicates you are not subscribed to.
/*
var _SUBSCRIBED_TO_PRIMARY = (
    'a direct subscriber to bug {primary_bug_id}, of which this bug, ' +
        '{bug_id}, is marked a duplicate.');
var YOU_SUBSCRIBED_TO_PRIMARY = _BECAUSE_YOU_ARE + _SUBSCRIBED_TO_PRIMARY;
var TEAM_SUBSCRIBED_TO_PRIMARY = _BECAUSE_TEAM_IS + _SUBSCRIBED_TO_PRIMARY;
var ADMIN_TEAM_SUBSCRIBED_TO_PRIMARY = (
    _ADMIN_BECAUSE_TEAM_IS + _SUBSCRIBED_TO_PRIMARY);
var TEAMS_SUBSCRIBED_TO_PRIMARY = _BECAUSE_TEAMS_ARE + _SUBSCRIBED_TO_PRIMARY;
var ADMIN_TEAMS_SUBSCRIBED_TO_PRIMARY = (
    _ADMIN_BECAUSE_TEAMS_ARE + _SUBSCRIBED_TO_PRIMARY);
*/

/* These are the owner variations. */
var _OWNER = (
    "the owner of the {pillar_type} " +
        "<a href='{pillar_url}'>{pillar_name}</a>, which has no bug " +
        "supervisor.");
/* These are the actual strings to use. */
var YOU_OWNER = _BECAUSE_YOU_ARE + _OWNER;
var TEAM_OWNER = _BECAUSE_TEAM_IS + _OWNER;
var ADMIN_TEAM_OWNER = _ADMIN_BECAUSE_TEAM_IS + _OWNER;
var TEAMS_OWNER = _BECAUSE_TEAMS_ARE + _OWNER;

// That's 27 options.
// - 5 options for "subscribed to primary" variations
// + 5 options for "duplicates plural"
// Also: "You are not subscribed to this bug." or similar.
// Also: "You have muted all email from this bug."

function add_subscription(config) {
    console.log(LP.cache.bug_subscription_info);
    
}
namespace.add_subscription = add_subscription

}, '0.1', {requires: [
    'dom', 'node', 'substitute'
]});
