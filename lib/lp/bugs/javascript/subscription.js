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
 * Store complete subscription 'reasons' for easier overriding and testing.
 *
 * Other 'reasons' are added to the object as required string components
 * are defined.
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
    'a direct subscriber to bug {duplicate_bug}, which is marked as a ' +
        'duplicate of this bug, {bug_id}');
var _SUBSCRIBED_TO_DUPLICATES = (
    'a direct subscriber to bugs {duplicate_bugs}, which are marked as ' +
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
        "{pillar}, which has no bug supervisor.");
/* These are the actual strings to use. */
Y.mix(reasons, {
    YOU_OWNER: _BECAUSE_YOU_ARE + _OWNER,
    TEAM_OWNER: _BECAUSE_TEAM_IS + _OWNER,
    ADMIN_TEAM_OWNER: _ADMIN_BECAUSE_TEAM_IS + _OWNER,
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

/**
 * ObjectLink class to unify link elements for better consistency.
 * Needed because some objects expose `title`, others expose `display_name`.
 */
ObjectLink = function(self, title, url) {
    return {
        self: self,
        title: title,
        url: url
    };
}

/**
 * Convert a context object to a { title, url } object for use in web pages.
 * Uses `display_name` and `web_link` attributes.
 * Additionally, accepts a string as well and returns it unmodified.
 */
function get_link_data(context) {
    // For testing, we take strings as well.
    if (typeof(context) == 'string') {
        return context;
    } else {
        return ObjectLink(context, context.display_name, context.web_link);
    }
}

/**
 * Convert a bug object to a { title, url } object for use in web pages.
 * Uses `id` and `web_link` attributes.
 * Additionally, accepts a string as well and returns it unmodified.
 */
function get_bug_link_data(bug) {
    // For testing, we take strings as well.
    if (typeof(bug) == 'string') {
        return bug;
    } else {
        return ObjectLink(bug, 'bug #' + bug.id.toString(), bug.web_link);
    }
}

/**
 * Gather all team subscriptions and sort them by the role: member/admin.
 * Returns up to 2 different subscription records, one for all teams
 * a person is a member of, and another for all teams a person is
 * an admin for.
 * With one team in a subscription, variable `team` is set, and with more
 * than one, variable `teams` is set containing all the teams.
 */
function gather_subscriptions_by_role(
    category, team_singular, team_plural,
    admin_team_singular, admin_team_plural) {
    var subscriptions = [];
    if (category.as_team_member.length > 0) {
        var teams = [];
        for (var index in category.as_team_member) {
            var team_subscription = category.as_team_member[index];
            teams.push(get_link_data(team_subscription.principal));
        }
        var sub = choose_by_number(
            category.as_team_member.length,
            { reason: team_singular,
              vars: {
                  team: teams[0] } },
            { reason: team_plural,
              vars: {
                  teams: teams } });
        subscriptions.push(sub);
    }

    if (category.as_team_admin.length > 0) {
        var teams = [];
        for (var index in category.as_team_admin) {
            var team_subscription = category.as_team_admin[index];
            teams.push(get_link_data(team_subscription.principal));
        }
        var sub = choose_by_number(
            category.as_team_admin.length,
            { reason: admin_team_singular,
              vars: {
                  team: teams[0] } },
            { reason: admin_team_plural,
              vars: {
                  teams: teams } });
        subscriptions.push(sub);
    }

    return subscriptions;
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

    // We add all the team assignments grouped by roles in the team.
    return subscriptions.concat(
        gather_subscriptions_by_role(
            category, reasons.TEAM_ASSIGNED, reasons.TEAMS_ASSIGNED,
            reasons.ADMIN_TEAM_ASSIGNED, reasons.ADMIN_TEAMS_ASSIGNED));
}
namespace._gather_subscriptions_as_assignee = gather_subscriptions_as_assignee;

/**
 * Gather subscription information for implicit bug supervisor.
 */
function gather_subscriptions_as_supervisor(category) {
    var subscriptions = [];
    var reasons = namespace._reasons;

    for (var index in category.personal) {
        var subscription = category.personal[index];
        subscriptions.push({
            reason: reasons.YOU_OWNER,
            vars: {
                pillar: get_link_data(subscription.pillar)
            }
        });
    }

    for (var index in category.as_team_member) {
        var team_subscription = category.as_team_member[index];
        subscriptions.push({
            reason: reasons.TEAM_OWNER,
            vars: {
                team: get_link_data(team_subscription.principal),
                pillar: get_link_data(team_subscription.pillar)
            }
        });
    }

    for (var index in category.as_team_admin) {
        var team_subscription = category.as_team_admin[index];
        subscriptions.push({
            reason: reasons.ADMIN_TEAM_OWNER,
            vars: {
                team: get_link_data(team_subscription.principal),
                pillar: get_link_data(team_subscription.pillar)
            }
        });
    }

    return subscriptions;
}
namespace._gather_subscriptions_as_supervisor =
        gather_subscriptions_as_supervisor;

function gather_dupe_subscriptions_by_team(team_subscriptions,
                                           singular, plural) {
    var subscriptions = [];

    // Collated list of { team: ..., bugs: []} records.
    var dupes_by_teams = [];
    for (var index in team_subscriptions) {
        var subscription = team_subscriptions[index];
        // Find the existing team reference.
        var added_bug = false;
        for (var team_dupes_idx in dupes_by_teams) {
            var team_dupes = dupes_by_teams[team_dupes_idx];
            if (team_dupes.team == subscription.principal) {
                team_dupes.bugs.push(get_bug_link_data(subscription.bug));
                added_bug = true;
                break;
            }
        }
        if (!added_bug) {
            dupes_by_teams.push({
                team: subscription.principal,
                bugs: [get_bug_link_data(subscription.bug)]
            });
        }
    }
    for (var team_dupes_idx in dupes_by_teams) {
        var team_dupes = dupes_by_teams[team_dupes_idx];
        var sub = choose_by_number(
            team_dupes.bugs.length,
            { reason: singular,
              vars: { duplicate_bug: team_dupes.bugs[0],
                      team: get_link_data(team_dupes.team) }},
            { reason: plural,
              vars: { duplicate_bugs: team_dupes.bugs,
                      team: get_link_data(team_dupes.team) }});
        subscriptions.push(sub);
    }
    return subscriptions;
}

/**
 * Gather subscription information from duplicate bug subscriptions.
 */
function gather_subscriptions_from_duplicates(category) {
    var subscriptions = [];
    var reasons = namespace._reasons;

    if (category.personal.length > 0) {
        var dupes = [];
        for (var index in category.personal) {
            var subscription = category.personal[index];
            dupes.push(
                get_bug_link_data(subscription.bug));
        }
        var sub = choose_by_number(
            dupes.length,
            { reason: reasons.YOU_SUBSCRIBED_TO_DUPLICATE,
              vars: { duplicate_bug: dupes[0] }},
            { reason: reasons.YOU_SUBSCRIBED_TO_DUPLICATES,
              vars: { duplicate_bugs: dupes }});
        subscriptions.push(sub);
    }

    // Get subscriptions as team member, grouped by teams.
    subscriptions = subscriptions.concat(
        gather_dupe_subscriptions_by_team(
            category.as_team_member,
            reasons.TEAM_SUBSCRIBED_TO_DUPLICATE,
            reasons.TEAM_SUBSCRIBED_TO_DUPLICATES));

    // Get subscriptions as team admin, grouped by teams.
    subscriptions = subscriptions.concat(
        gather_dupe_subscriptions_by_team(
            category.as_team_admin,
            reasons.ADMIN_TEAM_SUBSCRIBED_TO_DUPLICATE,
            reasons.ADMIN_TEAM_SUBSCRIBED_TO_DUPLICATES));

    return subscriptions;
}
namespace._gather_subscriptions_from_duplicates =
        gather_subscriptions_from_duplicates;

/**
 * Gather subscription information from direct team subscriptions.
 */
function gather_subscriptions_through_team(category) {
    var reasons = namespace._reasons;
    return gather_subscriptions_by_role(
        category, reasons.TEAM_SUBSCRIBED, reasons.TEAMS_SUBSCRIBED,
        reasons.ADMIN_TEAM_SUBSCRIBED, reasons.ADMIN_TEAMS_SUBSCRIBED);
}
namespace._gather_subscriptions_through_team =
        gather_subscriptions_through_team;

/**
 * Gather all non-direct subscriptions into a list.
 */
function gather_nondirect_subscriptions(info) {
    var subscriptions = [];

    return subscriptions
        .concat(gather_subscriptions_as_assignee(info.as_assignee))
        .concat(gather_subscriptions_from_duplicates(info.from_duplicate))
        .concat(gather_subscriptions_through_team(info.direct))
        .concat(gather_subscriptions_as_supervisor(info.as_owner));

}

function get_subscription_reason(config) {
    // Allow tests to pass subscription_info directly in.
    var info = config.subscription_info || LP.cache.bug_subscription_info;
    console.log(info);
    replace_textual_references(info, LP.cache);

    var subs = gather_nondirect_subscriptions(info);
    console.log(subs);

}
namespace.get_subscription_reason = get_subscription_reason

}, '0.1', {requires: [
    'dom', 'node', 'substitute'
]});
