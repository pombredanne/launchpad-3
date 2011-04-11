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

/**
 * Store complete reasons for easier overriding and testing.
 *
 * Other reasons are mixed in as needed string components are defined.
 */
var reasons = {
    NOT_SUBSCRIBED: "You are not subscribed to this bug.",
    MUTED_SUBSCRIPTION: "You have muted all email from this bug."
};
namespace._reasons = reasons;

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
Y.mix(reasons, {
    YOU_ASSIGNED: _BECAUSE_YOU_ARE + _ASSIGNED,
    TEAM_ASSIGNED: _BECAUSE_TEAM_IS + _ASSIGNED,
    ADMIN_TEAM_ASSIGNED: _ADMIN_BECAUSE_TEAM_IS + _ASSIGNED,
    TEAMS_ASSIGNED: _BECAUSE_TEAMS_ARE + _ASSIGNED,
    ADMIN_TEAMS_ASSIGNED: _ADMIN_BECAUSE_TEAMS_ARE + _ASSIGNED
});

/* These are the direct subscription variations. */
var _SUBSCRIBED = 'directly subscribed to it.';
var _MAY_HAVE_BEEN_CREATED = ' This subscription may have been created ';
var _YOU_SUBSCRIBED = _BECAUSE_YOU_ARE + _SUBSCRIBED;

/* Now these are the actual options we use. */
Y.mix(reasons, {
    YOU_SUBSCRIBED: _YOU_SUBSCRIBED,
    YOU_REPORTED: (_YOU_SUBSCRIBED + _MAY_HAVE_BEEN_CREATED +
                    'when you reported the bug.'),
    YOU_SUBSCRIBED_BUG_SUPERVISOR: (
        _YOU_SUBSCRIBED + _MAY_HAVE_BEEN_CREATED +
            'because the bug was private and you are a bug supervisor.'),
    YOU_SUBSCRIBED_SECURITY_CONTACT: (
        _YOU_SUBSCRIBED + _MAY_HAVE_BEEN_CREATED +
            'because the bug was security related and you are ' +
            'a security contact.'),
    TEAM_SUBSCRIBED: _BECAUSE_TEAM_IS + _SUBSCRIBED,
    ADMIN_TEAM_SUBSCRIBED: _ADMIN_BECAUSE_TEAM_IS + _SUBSCRIBED,
    TEAMS_SUBSCRIBED: _BECAUSE_TEAMS_ARE + _SUBSCRIBED,
    ADMIN_TEAMS_SUBSCRIBED: _ADMIN_BECAUSE_TEAMS_ARE + _SUBSCRIBED
});

/* These are the duplicate bug variations. */
var _SUBSCRIBED_TO_DUPLICATE = (
    'a direct subscriber to bug {dupe_bug_id}, which is marked as a ' +
        'duplicate of this bug, {bug_id}');
var _SUBSCRIBED_TO_DUPLICATES = (
    'a direct subscriber to bugs {dupe_bug_ids}, which are marked as ' +
        'duplicates of this bug, {bug_id}');
/* These are the actual strings to use. */
Y.mix(reasons, {
    YOU_SUBSCRIBED_TO_DUPLICATE: _BECAUSE_YOU_ARE + _SUBSCRIBED_TO_DUPLICATE,
    YOU_SUBSCRIBED_TO_DUPLICATES: (
        _BECAUSE_YOU_ARE + _SUBSCRIBED_TO_DUPLICATES),
    TEAM_SUBSCRIBED_TO_DUPLICATE: _BECAUSE_TEAM_IS + _SUBSCRIBED_TO_DUPLICATE,
    TEAM_SUBSCRIBED_TO_DUPLICATES: (
        _BECAUSE_TEAM_IS + _SUBSCRIBED_TO_DUPLICATES),
    ADMIN_TEAM_SUBSCRIBED_TO_DUPLICATE: (
        _ADMIN_BECAUSE_TEAM_IS + _SUBSCRIBED_TO_DUPLICATE),
    ADMIN_TEAM_SUBSCRIBED_TO_DUPLICATES: (
        _ADMIN_BECAUSE_TEAM_IS + _SUBSCRIBED_TO_DUPLICATES),
});

/* These are the owner variations. */
var _OWNER = (
    "the owner of the {pillar_type} " +
        "<a href='{pillar_url}'>{pillar_name}</a>, which has no bug " +
        "supervisor.");
/* These are the actual strings to use. */
Y.mix(reasons, {
    YOU_OWNER: _BECAUSE_YOU_ARE + _OWNER,
    TEAM_OWNER: _BECAUSE_TEAM_IS + _OWNER,
    ADMIN_TEAM_OWNER: _ADMIN_BECAUSE_TEAM_IS + _OWNER,
    TEAMS_OWNER: _BECAUSE_TEAMS_ARE + _OWNER,
});


/**
 * Return appropriate object based on the number.
 *
 * @method choose_by_number.
 * @param {Integer} number Number used in the string.
 * @param {Object} singular Object to return when number == 1.
 * @param {Object} plural Object to return when number != 1.
 */
function choose_by_number(number, singular, plural) {
    if (number == 1) {
        return singular;
    } else {
        return plural;
    }
}
namespace._choose_by_number = choose_by_number;

/**
 * Replaces textual references in `info` with actual objects from `cache`.
 *
 * This assumes that object references are specified with strings
 * starting with 'subscription-cache-reference', and are direct keys
 * for objects in `cache`.
 *
 * @param {Object} info Object to recursively look for references through.
 * @param {Object} cache Cache containing the objects indexed by their
 *                       references.
 */
function replace_textual_references(info, cache) {
    for (var key in info) {
        switch (typeof info[key]){
        case "object":
            replace_textual_references(info[key], cache);
            break;
        case "string":
            var ref_string = "subscription-cache-reference-";
            if (info[key].substring(0, ref_string.length) == ref_string) {
                info[key] = cache[info[key]];
            }
            break;
        default: break;
        }
    }
}
namespace._replace_textual_references = replace_textual_references;

function get_category_reason(
    category, personal, team_singular, team_plural,
    admin_team_singular, admin_team_plural) {
    var reason, teams;
    if (category.personal.length > 0) {
        reason = personal;
    } else if (category.as_team_member.length > 0) {
        reason = choose_by_number(
            category.as_team_member.length, team_singular, team_plural);
    } else if (category.as_team_admin.length > 0) {
        reason = choose_by_number(
            category.as_team_admin.length,
            admin_team_singular, admin_team_plural);
    }
    return reason;
}

function get_direct_reason(direct) {
    var reasons = namespace._reasons;
    var reason = get_category_reason(
        direct, reasons.YOU_SUBSCRIBED,
        reasons.TEAM_SUBSCRIBED, reasons.TEAMS_SUBSCRIBED,
        reasons.ADMIN_TEAM_SUBSCRIBED, reasons.ADMIN_TEAMS_SUBSCRIBED);
}

function get_assignee_reason(assignee) {
    var reasons = namespace._reasons;
    return get_category_reason(
        assignee, reasons.YOU_ASSIGNED,
        reasons.TEAM_ASSIGNED, reasons.TEAMS_ASSIGNED,
        reasons.ADMIN_TEAM_ASSIGNED, reasons.ADMIN_TEAMS_ASSIGNED);
}

/**
 * Gather subscription information for assignee.
 */
function gather_subscriptions_as_assignee(category) {
    var subscriptions = [];
    var reasons = namespace._reasons;

    if (category.personal.length > 0) {
        subscriptions.push(
            { reason: reasons.YOU_ASSIGNED,
              vars: {} });
    }

    if (category.as_team_member.length > 0) {
        var teams = [];
        for (var index in category.as_team_member) {
            var team_subscription = category.as_team_member[index];
            teams.push(team_subscription.principal);
        }
        var sub = choose_by_number(
            category.as_team_member.length,
            { reason: reasons.TEAM_ASSIGNED,
              vars: {
                  team: teams[0] } },
            { reason: reasons.TEAMS_ASSIGNED,
              vars: {
                  teams: teams } });
        subscriptions.push(sub);
    }

    if (category.as_team_admin.length > 0) {
        var teams = [];
        for (var index in category.as_team_admin) {
            var team_subscription = category.as_team_admin[index];
            teams.push(team_subscription.principal);
        }
        var sub = choose_by_number(
            category.as_team_admin.length,
            { reason: reasons.ADMIN_TEAM_ASSIGNED,
              vars: {
                  team: teams[0] } },
            { reason: reasons.ADMIN_TEAMS_ASSIGNED,
              vars: {
                  teams: teams } });
        subscriptions.push(sub);
    }

    return subscriptions;
}
namespace._gather_subscriptions_as_assignee = gather_subscriptions_as_assignee;

/**
 * Gather all non-direct subscriptions into a list.
 */
function gather_nondirect_subscriptions(info) {
    var subscriptions = [];

    return subscriptions
        .concat(gather_subscriptions_as_assignee(info.as_assignee))
        .concat(gather_subscriptions_from_duplicate(info.from_duplicate))
        .concat(gather_subscriptions_through_team(info.direct))
        .concat(gather_subscriptions_as_owner(info.direct));

}

function get_subscription_reason(config) {
    // Allow tests to pass subscription_info directly in.
    var info = config.subscription_info || LP.cache.bug_subscription_info;
    console.log(info);
    replace_textual_references(info, LP.cache);
    // Is there more than one subscription type.
    var has_multiple = (
        ((info.as_assignee.count > 0)? 1 : 0) +
            ((info.direct.count > 0)? 1 : 0) +
            ((info.as_owner.count > 0)? 1 : 0) +
            ((info.from_duplicate.count > 0)? 1 : 0)) > 1;
    var reason;
    if (info.direct.count > 0) {
        reason = get_direct_reason(info.direct);
        // To reduce indentation and avoid an 'else', return now.
        return {
            reason: reason,
            has_multiple: has_multiple
        };
    }

    if (info.as_assignee.count > 0) {
        reason = get_assignee_reason(info.as_assignee);
        // To reduce indentation and avoid an 'else', return now.
        return {
            reason: reason,
            has_multiple: has_multiple
        };
    }

    // User is not an assignee.
    return {
        reason: reason,
        has_multiple: has_multiple
    };
}
namespace.get_subscription_reason = get_subscription_reason

}, '0.1', {requires: [
    'dom', 'node', 'substitute'
]});
