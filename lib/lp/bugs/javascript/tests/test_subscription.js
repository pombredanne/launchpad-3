YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.subscription', function(Y) {

var suite = new Y.Test.Suite("lp.bugs.subscription Tests");
var module = Y.lp.bugs.subscription;

/**
 * Test selection of the string by the number.
 * We expect to receive a plural string for all numbers
 * not equal to 1, and a singular string otherwise.
 */
suite.add(new Y.Test.Case({
    name: 'Choose object by number',

    test_singular: function() {
        Y.Assert.areEqual(
            'SINGULAR',
            module._choose_by_number(1, 'SINGULAR', 'PLURAL'));
    },

    test_plural: function() {
        Y.Assert.areEqual(
            'PLURAL',
            module._choose_by_number(5, 'SINGULAR', 'PLURAL'));
    },

    test_zero: function() {
        Y.Assert.areEqual(
            'PLURAL',
            module._choose_by_number(0, 'SINGULAR', 'PLURAL'));
    }
}));

/**
 * Replacing references to cache objects with actual objects.
 */
suite.add(new Y.Test.Case({
    name: 'Replacing references with real objects',

    test_nothing: function() {
        // When there are no references, nothing gets replaced.
        var object = {
            something: 'nothing'
        };
        var cache = {};
        module._replace_textual_references(object, cache)
        Y.Assert.areEqual('nothing', object.something);
    },

    test_simple: function() {
        // With a simple reference, it gets substituted.
        var object = {
            something: 'subscription-cache-reference-1'
        };
        var cache = {
            'subscription-cache-reference-1': 'OK'
        };
        module._replace_textual_references(object, cache);
        Y.Assert.areEqual('OK', object.something);
    },

    test_multiple: function() {
        // With multiple references, they all get substituted.0
        var object = {
            something: 'subscription-cache-reference-1',
            other: 'subscription-cache-reference-2'
        };
        var cache = {
            'subscription-cache-reference-1': 'OK 1',
            'subscription-cache-reference-2': 'OK 2'
        };
        module._replace_textual_references(object, cache);
        Y.Assert.areEqual('OK 1', object.something);
        Y.Assert.areEqual('OK 2', object.other);
    },

    test_recursive: function() {
        // Even references in nested objects get replaced.
        var object = {
            nested: {
                something: 'subscription-cache-reference-1'
            }
        };
        var cache = {
            'subscription-cache-reference-1': 'OK'
        };
        module._replace_textual_references(object, cache);
        Y.Assert.areEqual('OK', object.nested.something);
    }
}));


/**
 * Gather subscription records for all assignments.
 */
suite.add(new Y.Test.Case({
    name: 'Gather assignment subscription information',

    test_nothing: function() {
        // When there are no subscriptions as assignee, returns empty list.
        var mock_category = {
            count: 0,
            personal: [],
            as_team_member: [],
            as_team_admin: []
        };
        Y.ArrayAssert.itemsAreEqual(
            [],
            module._gather_subscriptions_as_assignee(mock_category));
    },

    test_personal: function() {
        // When a person is directly the bug assignee, we get that
        // subscription details returned.
        var mock_category = {
            count: 1,
            personal: [{}],
            as_team_member: [],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(module._reasons.YOU_ASSIGNED, subs[0].reason);
        Y.Assert.areEqual(module._actions.CHANGE_ASSIGNEES, subs[0].action);
    },

    test_team_member: function() {
        // When a person is the bug assignee through team membership,
        // we get that subscription details returned.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [{ principal: 'my team'}],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(module._reasons.TEAM_ASSIGNED, subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        Y.Assert.areEqual(module._actions.CONTACT_TEAMS, subs[0].action);
    },

    test_team_member_multiple: function() {
        // If a person is a member of multiple teams are assigned to work
        // on a single bug (eg. on different bug tasks) they get only one
        // subscription returned.
        var mock_category = {
            count: 2,
            personal: [],
            as_team_member: [{ principal: 'team1'},
                             { principal: 'team2'}],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(module._reasons.TEAMS_ASSIGNED, subs[0].reason);
        // And there is a 'teams' variable containing all the team objects.
        Y.ArrayAssert.itemsAreEqual(['team1', 'team2'],
                                    subs[0].vars.teams);
        Y.Assert.areEqual(module._actions.CONTACT_TEAMS, subs[0].action);
    },

    test_team_member_multiple_duplicate: function() {
        // As with the previous test, but we need to show that each team is
        // only represented once even if they are responsible for multiple
        // bug tasks.
        // We test with full-fledged objects to make sure they work with the
        // mechanism used to find dupes.
        var team1 = {display_name: 'team 1',
                     web_link: 'http://launchpad.net/~team1'},
            team2 = {display_name: 'team 2',
                     web_link: 'http://launchpad.net/~team2'},
            mock_category = {
                count: 2,
                personal: [],
                as_team_member: [{ principal: team1 },
                                 { principal: team2 },
                                 { principal: team2 },],
                as_team_admin: []
            },
            subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(module._reasons.TEAMS_ASSIGNED, subs[0].reason);
        // And there is a 'teams' variable containing all the team objects.
        var teams_found = [];
        for (var index in subs[0].vars.teams) {
            teams_found.push(subs[0].vars.teams[index].title);
        }
        Y.ArrayAssert.itemsAreEqual(['team 1', 'team 2'], teams_found);
    },

    test_team_admin: function() {
        // When a person is the bug assignee through team membership,
        // and a team admin at the same time, that subscription is returned.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [],
            as_team_admin: [{ principal: 'my team' }],
        };
        var subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.ADMIN_TEAM_ASSIGNED, subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        Y.Assert.areEqual(module._actions.CHANGE_ASSIGNEES, subs[0].action);
    },

    test_team_admin_multiple: function() {
        // If a person is a member of multiple teams are assigned to work
        // on a single bug (eg. on different bug tasks) they get only one
        // subscription returned.
        var mock_category = {
            count: 2,
            personal: [],
            as_team_member: [],
            as_team_admin: [{ principal: 'team1'},
                             { principal: 'team2'}],
        };
        var subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.ADMIN_TEAMS_ASSIGNED, subs[0].reason);
        // And there is a 'teams' variable containing all the team objects.
        Y.ArrayAssert.itemsAreEqual(['team1', 'team2'],
                                    subs[0].vars.teams);
        Y.Assert.areEqual(module._actions.CHANGE_ASSIGNEES, subs[0].action);
    },

    test_team_admin_multiple_duplicate: function() {
        // As with the previous test, but we need to show that each team is
        // only represented once even if they are responsible for multiple
        // bug tasks.
        // We test with full-fledged objects to make sure they work with the
        // mechanism used to find dupes.
        var team1 = {display_name: 'team 1',
                     web_link: 'http://launchpad.net/~team1'},
            team2 = {display_name: 'team 2',
                     web_link: 'http://launchpad.net/~team2'},
            mock_category = {
                count: 2,
                personal: [],
                as_team_admin: [{ principal: team1 },
                                { principal: team2 },
                                { principal: team2 },],
                as_team_member: []
            },
            subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(1, subs.length);
        // And there is a 'teams' variable containing all the team objects.
        var teams_found = [];
        for (var index in subs[0].vars.teams) {
            teams_found.push(subs[0].vars.teams[index].title);
        }
        Y.ArrayAssert.itemsAreEqual(['team 1', 'team 2'], teams_found);
    },

    test_combined: function() {
        // Test that multiple assignments, even if they are in different
        // categories, work properly.
        var mock_category = {
            count: 3,
            personal: [{}],
            as_team_member: [{ principal: 'users' }],
            as_team_admin: [{ principal: 'admins' }],
        };
        var subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(3, subs.length);
    },

    test_object_links: function() {
        // Test that team assignments actually provide decent link data.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [
                { principal: { display_name: 'My team',
                               web_link: 'http://link' } }],
            as_team_admin: [],
        };
        var subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual('My team', subs[0].vars.team.title);
        Y.Assert.areEqual('http://link', subs[0].vars.team.url);
    },
}));

/**
 * Gather subscription records for bug supervisor.
 */
suite.add(new Y.Test.Case({
    name: 'Gather bug supervisor subscription information',

    test_nothing: function() {
        // When there are no subscriptions as bug supervisor,
        // returns empty list.
        var mock_category = {
            count: 0,
            personal: [],
            as_team_member: [],
            as_team_admin: []
        };
        Y.ArrayAssert.itemsAreEqual(
            [],
            module._gather_subscriptions_as_supervisor(mock_category));
    },

    test_personal: function() {
        // Person is the implicit bug supervisor by being the owner
        // of the project with no bug supervisor.
        var mock_category = {
            count: 1,
            personal: [{pillar: 'project'}],
            as_team_member: [],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_as_supervisor(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(module._reasons.YOU_OWNER, subs[0].reason);
        Y.Assert.areEqual('project', subs[0].vars.pillar);
        Y.Assert.areEqual(module._actions.SET_BUG_SUPERVISOR, subs[0].action);
    },

    test_personal_multiple: function() {
        // Person is the implicit bug supervisor by being the owner
        // of several projects (eg. multiple bug tasks) with no bug
        // supervisor.
        var mock_category = {
            count: 2,
            personal: [{pillar: 'project'}, {pillar: 'distro'}],
            as_team_member: [],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_as_supervisor(mock_category);
        Y.Assert.areEqual(2, subs.length);
    },

    test_team_member: function() {
        // Person is a member of the team which is the implicit
        // bug supervisor.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [{ principal: 'my team',
                               pillar: 'project' }],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_as_supervisor(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(module._reasons.TEAM_OWNER, subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        Y.Assert.areEqual('project', subs[0].vars.pillar);
        Y.Assert.areEqual(module._actions.CONTACT_TEAMS, subs[0].action);
    },

    test_team_member_multiple: function() {
        // Person is a member of several teams which are implicit bug
        // supervisors on multiple bugtasks, we get subscription
        // records separately.
        var mock_category = {
            count: 2,
            personal: [],
            as_team_member: [{ principal: 'team1',
                               pillar: 'project' },
                             { principal: 'team2',
                               pillar: 'distro' }],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_as_supervisor(mock_category);
        Y.Assert.areEqual(2, subs.length);
    },

    test_team_admin: function() {
        // Person is an admin of the team which is the implicit
        // bug supervisor.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [],
            as_team_admin: [{ principal: 'my team',
                              pillar: 'project' }],
        };
        var subs = module._gather_subscriptions_as_supervisor(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.ADMIN_TEAM_OWNER, subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        Y.Assert.areEqual('project', subs[0].vars.pillar);
        Y.Assert.areEqual(module._actions.SET_BUG_SUPERVISOR, subs[0].action);
    },

    test_team_admin_multiple: function() {
        // Person is an admin of several teams which are implicit bug
        // supervisors on multiple bugtasks, we get subscription
        // records separately.
        var mock_category = {
            count: 2,
            personal: [],
            as_team_member: [],
            as_team_admin: [{ principal: 'team1',
                               pillar: 'project' },
                             { principal: 'team2',
                               pillar: 'distro' }]
        };
        var subs = module._gather_subscriptions_as_supervisor(mock_category);
        Y.Assert.areEqual(2, subs.length);
    },

    test_combined: function() {
        // Test that multiple implicit bug supervisor roles
        // are all returned.
        var mock_category = {
            count: 3,
            personal: [{pillar: 'project1'}],
            as_team_member: [{ principal: 'users', pillar: 'project2' }],
            as_team_admin: [{ principal: 'admins', pillar: 'distro' }],
        };
        var subs = module._gather_subscriptions_as_assignee(mock_category);
        Y.Assert.areEqual(3, subs.length);
    },

    test_object_links: function() {
        // Test that team-as-supervisor actually provide decent link data,
        // along with pillars as well.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [{
                principal: { display_name: 'My team',
                             web_link: 'http://link' },
                pillar: { display_name: 'My project',
                          web_link: 'http://project/' }
            }],
            as_team_admin: [],
        };
        var subs = module._gather_subscriptions_as_supervisor(mock_category);
        Y.Assert.areEqual('My team', subs[0].vars.team.title);
        Y.Assert.areEqual('http://link', subs[0].vars.team.url);

        Y.Assert.areEqual('My project', subs[0].vars.pillar.title);
        Y.Assert.areEqual('http://project/', subs[0].vars.pillar.url);
    },
}));

/**
 * Gather subscription records for dupe bug subscriptions.
 */
suite.add(new Y.Test.Case({
    name: 'Gather subscription information for duplicates',

    test_nothing: function() {
        // When there are no duplicate subscriptions, returns empty list.
        var mock_category = {
            count: 0,
            personal: [],
            as_team_member: [],
            as_team_admin: []
        };
        Y.ArrayAssert.itemsAreEqual(
            [],
            module._gather_subscriptions_from_duplicates(mock_category));
    },

    test_personal: function() {
        // A person is subscribed to a duplicate bug.
        var mock_category = {
            count: 1,
            personal: [{bug: 'dupe bug'}],
            as_team_member: [],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.YOU_SUBSCRIBED_TO_DUPLICATE, subs[0].reason);
        Y.Assert.areEqual('dupe bug', subs[0].vars.duplicate_bug);
        Y.Assert.areEqual(module._actions.UNSUBSCRIBE_DUPLICATES,
                          subs[0].action);
    },

    test_personal_multiple: function() {
        // A person is subscribed to multiple duplicate bugs.
        // They are returned together as one subscription record.
        var mock_category = {
            count: 2,
            personal: [{bug: 'dupe1'}, {bug: 'dupe2'}],
            as_team_member: [],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.YOU_SUBSCRIBED_TO_DUPLICATES, subs[0].reason);
        Y.ArrayAssert.itemsAreEqual(
            ['dupe1', 'dupe2'], subs[0].vars.duplicate_bugs);
        Y.Assert.areEqual(module._actions.UNSUBSCRIBE_DUPLICATES,
                          subs[0].action);
    },

    test_team_member: function() {
        // A person is a member of the team subscribed to a duplicate bug.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [{ principal: 'my team',
                               bug: 'dupe' }],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.TEAM_SUBSCRIBED_TO_DUPLICATE, subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        // And a 'duplicate_bug' variable pointing to the dupe.
        Y.Assert.areEqual('dupe', subs[0].vars.duplicate_bug);
        Y.Assert.areEqual(module._actions.CONTACT_TEAMS, subs[0].action);
    },

    test_team_member_multiple_bugs: function() {
        // A person is a member of the team subscribed to multiple
        // duplicate bugs.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [{
                principal: 'my team',
                bug: 'dupe1'
            }, {
                principal: 'my team',
                bug: 'dupe2'
            }],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.TEAM_SUBSCRIBED_TO_DUPLICATES, subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        // And a 'duplicate_bugs' variable with the list of dupes.
        Y.ArrayAssert.itemsAreEqual(
            ['dupe1', 'dupe2'], subs[0].vars.duplicate_bugs);
        Y.Assert.areEqual(module._actions.CONTACT_TEAMS, subs[0].action);
    },

    test_team_member_multiple: function() {
        // A person is a member of several teams subscribed to
        // duplicate bugs.
        var mock_category = {
            count: 2,
            personal: [],
            as_team_member: [{ principal: 'team1',
                               bug: 'dupe1' },
                             { principal: 'team2',
                               bug: 'dupe1' }],
            as_team_admin: []
        };

        // Result is two separate subscription records.
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual(2, subs.length);
    },

    test_team_admin: function() {
        // A person is an admin of the team subscribed to a duplicate bug.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [],
            as_team_admin: [{ principal: 'my team',
                               bug: 'dupe' }]
        };
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.ADMIN_TEAM_SUBSCRIBED_TO_DUPLICATE,
            subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        // And a 'duplicate_bug' variable pointing to the dupe.
        Y.Assert.areEqual('dupe', subs[0].vars.duplicate_bug);
        Y.Assert.areEqual(module._actions.UNSUBSCRIBE_DUPLICATES,
                          subs[0].action);
    },

    test_team_admin_multiple_bugs: function() {
        // A person is an admin of the team subscribed to multiple
        // duplicate bugs.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [],
            as_team_admin: [{
                principal: 'my team',
                bug: 'dupe1'
            }, {
                principal: 'my team',
                bug: 'dupe2'
            }]
        };
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.ADMIN_TEAM_SUBSCRIBED_TO_DUPLICATES,
            subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        // And a 'duplicate_bugs' variable with the list of dupes.
        Y.ArrayAssert.itemsAreEqual(
            ['dupe1', 'dupe2'], subs[0].vars.duplicate_bugs);
        Y.Assert.areEqual(module._actions.UNSUBSCRIBE_DUPLICATES,
                          subs[0].action);
    },

    test_team_admin_multiple: function() {
        // A person is an admin of several teams subscribed to
        // duplicate bugs.
        var mock_category = {
            count: 2,
            personal: [],
            as_team_member: [],
            as_team_admin: [{ principal: 'team1',
                               bug: 'dupe1' },
                             { principal: 'team2',
                               bug: 'dupe1' }],
        };

        // Result is two separate subscription records.
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual(2, subs.length);
    },

    test_object_links: function() {
        // Test that team dupe subscriptions actually provide decent
        // link data, including duplicate bugs link data.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [{
                principal: { display_name: 'My team',
                             web_link: 'http://link' },
                bug: { id: 1,
                       web_link: 'http://launchpad/bug/1' }
            }],
            as_team_admin: [],
        };
        var subs = module._gather_subscriptions_from_duplicates(
            mock_category);
        Y.Assert.areEqual('My team', subs[0].vars.team.title);
        Y.Assert.areEqual('http://link', subs[0].vars.team.url);

        Y.Assert.areEqual('#1', subs[0].vars.duplicate_bug.title);
        Y.Assert.areEqual(
            'http://launchpad/bug/1', subs[0].vars.duplicate_bug.url);
    },
}));

/**
 * Gather subscription records for direct team subscriptions.
 */
suite.add(new Y.Test.Case({
    name: 'Gather team subscription information',

    test_nothing: function() {
        // When there are no subscriptions through team, returns empty list.
        var mock_category = {
            count: 0,
            personal: [],
            as_team_member: [],
            as_team_admin: []
        };
        Y.ArrayAssert.itemsAreEqual(
            [],
            module._gather_subscriptions_through_team(mock_category));
    },

    test_personal: function() {
        // A personal subscription is not considered a team subscription.
        var mock_category = {
            count: 1,
            personal: [{}],
            as_team_member: [],
            as_team_admin: []
        };
        Y.ArrayAssert.itemsAreEqual(
            [],
            module._gather_subscriptions_through_team(mock_category));
    },

    test_team_member: function() {
        // Person is a member of the team subscribed to the bug.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [{ principal: 'my team'}],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_through_team(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(module._reasons.TEAM_SUBSCRIBED, subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        Y.Assert.areEqual(module._actions.CONTACT_TEAMS, subs[0].action);
    },

    test_team_member_multiple: function() {
        // Person is a member of several teams subscribed to the bug.
        var mock_category = {
            count: 2,
            personal: [],
            as_team_member: [{ principal: 'team1'},
                             { principal: 'team2'}],
            as_team_admin: []
        };
        var subs = module._gather_subscriptions_through_team(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(module._reasons.TEAMS_SUBSCRIBED, subs[0].reason);
        // And there is a 'teams' variable containing all the team objects.
        Y.ArrayAssert.itemsAreEqual(['team1', 'team2'],
                                    subs[0].vars.teams);
        Y.Assert.areEqual(module._actions.CONTACT_TEAMS, subs[0].action);
    },

    test_team_member_multiple_duplicate: function() {
        // As with the previous test, but we need to show that each team is
        // only represented once even if they are responsible for multiple
        // bug tasks.
        // We test with full-fledged objects to make sure they work with the
        // mechanism used to find dupes.
        var team1 = {display_name: 'team 1',
                     web_link: 'http://launchpad.net/~team1'},
            team2 = {display_name: 'team 2',
                     web_link: 'http://launchpad.net/~team2'},
            mock_category = {
                count: 2,
                personal: [],
                as_team_member: [{ principal: team1 },
                                 { principal: team2 },
                                 { principal: team2 },],
                as_team_admin: []
            },
            subs = module._gather_subscriptions_through_team(mock_category);
        Y.Assert.areEqual(1, subs.length);
        // And there is a 'teams' variable containing all the team objects.
        var teams_found = [];
        for (var index in subs[0].vars.teams) {
            teams_found.push(subs[0].vars.teams[index].title);
        }
        Y.ArrayAssert.itemsAreEqual(['team 1', 'team 2'], teams_found);
    },

    test_team_admin: function() {
        // Person is an admin of the team subscribed to the bug.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [],
            as_team_admin: [{ principal: 'my team' }],
        };
        var subs = module._gather_subscriptions_through_team(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.ADMIN_TEAM_SUBSCRIBED, subs[0].reason);
        // And there is a 'team' variable containing the team object.
        Y.Assert.areEqual('my team', subs[0].vars.team);
        Y.Assert.areEqual(module._actions.CHANGE_TEAM_SUBSCRIPTIONS,
                          subs[0].action);
    },

    test_team_admin_multiple: function() {
        // Person is an admin of the several teams subscribed to the bug.
        var mock_category = {
            count: 2,
            personal: [],
            as_team_member: [],
            as_team_admin: [{ principal: 'team1'},
                             { principal: 'team2'}],
        };
        var subs = module._gather_subscriptions_through_team(mock_category);
        Y.Assert.areEqual(1, subs.length);
        Y.Assert.areEqual(
            module._reasons.ADMIN_TEAMS_SUBSCRIBED, subs[0].reason);
        // And there is a 'teams' variable containing all the team objects.
        Y.ArrayAssert.itemsAreEqual(['team1', 'team2'],
                                    subs[0].vars.teams);
        Y.Assert.areEqual(module._actions.CHANGE_TEAM_SUBSCRIPTIONS,
                          subs[0].action);
    },

    test_team_admin_multiple_duplicate: function() {
        // As with the previous test, but we need to show that each team is
        // only represented once even if they are responsible for multiple
        // bug tasks.
        // We test with full-fledged objects to make sure they work with the
        // mechanism used to find dupes.
        var team1 = {display_name: 'team 1',
                     web_link: 'http://launchpad.net/~team1'},
            team2 = {display_name: 'team 2',
                     web_link: 'http://launchpad.net/~team2'},
            mock_category = {
                count: 2,
                personal: [],
                as_team_admin: [{ principal: team1 },
                                { principal: team2 },
                                { principal: team2 },],
                as_team_member: []
            },
            subs = module._gather_subscriptions_through_team(mock_category);
        Y.Assert.areEqual(1, subs.length);
        // And there is a 'teams' variable containing all the team objects.
        var teams_found = [];
        for (var index in subs[0].vars.teams) {
            teams_found.push(subs[0].vars.teams[index].title);
        }
        Y.ArrayAssert.itemsAreEqual(['team 1', 'team 2'], teams_found);
    },

    test_combined: function() {
        // Test that multiple subscriptions, even if they are in different
        // categories, work properly, and that personal subscriptions are
        // still ignored.
        var mock_category = {
            count: 3,
            personal: [{}],
            as_team_member: [{ principal: 'users' }],
            as_team_admin: [{ principal: 'admins' }],
        };
        var subs = module._gather_subscriptions_through_team(mock_category);
        Y.Assert.areEqual(2, subs.length);
    },

    test_object_links: function() {
        // Test that team subscriptions actually provide decent link data.
        var mock_category = {
            count: 1,
            personal: [],
            as_team_member: [
                { principal: { display_name: 'My team',
                               web_link: 'http://link' } }],
            as_team_admin: [],
        };
        var subs = module._gather_subscriptions_through_team(mock_category);
        Y.Assert.areEqual('My team', subs[0].vars.team.title);
        Y.Assert.areEqual('http://link', subs[0].vars.team.url);
    },
}));


/**
 * Helper to construct a single 'category' of subscriptions,
 * grouped by type (personally, as team member and as team admin).
 */
function _constructCategory(personal, as_member, as_admin) {
    if (personal === undefined) {
        personal = [];
    }
    if (as_member === undefined) {
        as_member = [];
    }
    if (as_admin === undefined) {
        as_admin = [];
    }
    return {
        count: personal.length + as_admin.length + as_member.length,
        personal: personal,
        as_team_member: as_member,
        as_team_admin: as_admin
    };
}

/**
 * Get the reason for a direct subscription.
 * Tests for method get_direct_subscription_information().
 */
suite.add(new Y.Test.Case({
    name: 'Get reason for a direct subscription',

    _should: {
        error: {
            test_multiple_direct_subscriptions:
            new Error('A person should not have more than ' +
                      'one direct personal subscription.')
        }
    },

    test_multiple_direct_subscriptions: function() {
        // It should not be possible to have multiple direct,
        // personal subscriptions.
        // This errors out (see _should.error above).
        var info = {
            direct: _constructCategory(['1', '2']),
            count: 2
        };
        module._get_direct_subscription_information(info);
    },

    test_no_subscriptions: function() {
        // There are no subscriptions at all.
        var info = {
            direct: _constructCategory(),
            from_duplicates: _constructCategory()
        };
        info.count = info.direct.count + info.from_duplicates.count;

        Y.Assert.areEqual(
            module._reasons.NOT_SUBSCRIBED,
            module._get_direct_subscription_information(info));
    },

    test_no_direct_subscriptions: function() {
        // There is no direct subscription, but there are
        // other subscriptions.
        var info = {
            direct: _constructCategory(),
            from_duplicates: _constructCategory(['dupe'])
        };
        info.count = info.direct.count + info.from_duplicates.count;
        Y.Assert.areSame(
            module._reasons.NOT_PERSONALLY_SUBSCRIBED,
            module._get_direct_subscription_information(info));
    },

    test_muted_subscription: function() {
        // The direct subscription is muted.
        var info = {
            direct: _constructCategory(['direct']),
            muted: true,
        };
        info.count = info.direct.count;
        Y.Assert.areSame(
            module._reasons.MUTED_SUBSCRIPTION,
            module._get_direct_subscription_information(info));
    },

    test_direct_subscription: function() {
        // The simple direct subscription.
        var sub = {
            bug: {
                private: false,
                security_related: false,
            },
            principal_is_reporter: false,
        };
        var info = {
            direct: _constructCategory([sub]),
            count: 1
        };

        Y.Assert.areSame(
            module._reasons.YOU_SUBSCRIBED,
            module._get_direct_subscription_information(info));
    },

    test_direct_subscription_as_reporter: function() {
        // The direct subscription created for bug reporter.
        var sub = {
            bug: {},
            principal_is_reporter: true,
        };
        var info = {
            direct: _constructCategory([sub]),
            count: 1
        };
        Y.Assert.areSame(
            module._reasons.YOU_REPORTED,
            module._get_direct_subscription_information(info));
    },

    test_direct_subscription_for_supervisor: function() {
        // The direct subscription created on private bugs for
        // the bug supervisor.
        var sub = {
            bug: {
                private: true,
            },
        };
        var info = {
            direct: _constructCategory([sub]),
            count: 1
        };
        Y.Assert.areSame(
            module._reasons.YOU_SUBSCRIBED_BUG_SUPERVISOR,
            module._get_direct_subscription_information(info));
    },

    test_direct_subscription_for_security_contact: function() {
        // The simple direct subscription.
        var sub = {
            bug: {
                security_related: true,
            },
        };
        var info = {
            direct: _constructCategory([sub]),
            count: 1
        };
        Y.Assert.areSame(
            module._reasons.YOU_SUBSCRIBED_SECURITY_CONTACT,
            module._get_direct_subscription_information(info));
    },

}));

/**
 * Test for get_objectlink_html() method.
 */
suite.add(new Y.Test.Case({
    name: 'Test conversion of ObjectLink to HTML.',

    _should: {
        error: {
            test_non_link: new Error('Not a proper ObjectLink.')
        }
    },

    test_string: function() {
        // When a string is passed in, it is returned unmodified.
        var link = 'test';
        Y.Assert.areEqual(
            link,
            module._get_objectlink_html(link));
    },

    test_non_link: function() {
        // When an object that doesn't have both 'title' and 'url'
        // passed in, it fails. (see _should.error above)
        var link = {};
        module._get_objectlink_html(link);
    },

    test_simple: function() {
        // When a string is passed in, it is returned unmodified.
        var link = {
            title: 'Title',
            url: 'http://url/'
        };
        Y.Assert.areEqual(
            '<a href="http://url/">Title</a>',
            module._get_objectlink_html(link));
    },

    test_escaping_title: function() {
        // Even with title containing HTML characters, they are properly
        // escaped.
        var link = {
            title: 'Title<script>',
            url: 'http://url/'
        };
        Y.Assert.areEqual(
            '<a href="http://url/">Title&lt;script&gt;</a>',
            module._get_objectlink_html(link));
    },

    test_escaping_url: function() {
        // Even with title containing HTML characters, they are properly
        // escaped.
        var url = 'http://url/" onclick="javascript:alert(\'test\');" a="';
        var link = {
            title: 'Title',
            url: url
        };
        // Firefox returns:
        //  '<a href="http://url/%22%20onclick=%22' +
        //      'javascript:alert%28%27test%27%29;%22%20a=%22">Title</a>'
        // WebKit returns:
        //  '<a href="http://url/&quot; onclick=&quot;'+
        //      'javascript:alert(\'test\');&quot; a=&quot;">Title</a>'
        Y.Assert.areNotEqual(
            '<a href="' + url + '">Title</a>',
            module._get_objectlink_html(link));
    },

}));

/**
 * Test for safely_render_description() method.
 */
suite.add(new Y.Test.Case({
    name: 'Test variable substitution in subscription descriptions.',

    _should: {
        error: {
            test_non_link: new Error('Not a proper ObjectLink.')
        }
    },

    test_no_variables: function() {
        // For a string with no variables, no substitution is performed.
        var sub = {
            reason: 'test string with no vars',
            vars: { no: 'vars' }
        };

        Y.Assert.areEqual(
            sub.reason,
            module._safely_render_description(sub));
    },

    test_missing_variable: function() {
        // If a variable is missing, it is not substituted.
        var sub = {
            reason: 'test string with {foo}',
            vars: {}
        };

        Y.Assert.areEqual(
            'test string with {foo}',
            module._safely_render_description(sub));
    },

    test_string_variable: function() {
        // Plain string variables are directly substituted.
        var sub = {
            reason: 'test string with {foo}',
            vars: { foo: 'nothing' }
        };

        Y.Assert.areEqual(
            'test string with nothing',
            module._safely_render_description(sub));
    },

    _constructObjectLink: function(title, url) {
        // Constructs a mock ObjectLink.
        return { title: title, url: url };
    },

    test_objectlink_variable: function() {
        // ObjectLink variables get turned into actual HTML links.
        var sub = {
            reason: 'test string with {foo}',
            vars: { foo: this._constructObjectLink('Title', 'http://link/') }
        };

        Y.Assert.areEqual(
            'test string with <a href="http://link/">Title</a>',
            module._safely_render_description(sub));
    },

    test_multiple_variables: function() {
        // For multiple variables, they all get replaced.
        var sub = {
            reason: '{simple} string with {foo} {simple}',
            vars: {
                foo: this._constructObjectLink('Link', 'http://link/'),
                simple: "test"
            }
        };

        Y.Assert.areEqual(
            'test string with <a href="http://link/">Link</a> test',
            module._safely_render_description(sub));
    },

    test_extra_variable: function() {
        // Passing in extra variables causes them to be replaced as well.
        var sub = {
            reason: 'test string with {extra}',
            vars: {}
        };
        var extra_vars = {
            extra: 'something extra'
        };

        Y.Assert.areEqual(
            'test string with something extra',
            module._safely_render_description(sub, extra_vars));
    },

    test_extra_objectlink_variable: function() {
        // Passing in extra ObjectLink variable gets properly substituted.
        var sub = {
            reason: 'test string with {extra}',
            vars: {}
        };
        var extra_vars = {
            extra: this._constructObjectLink('extras', 'http://link/')
        };

        Y.Assert.areEqual(
            'test string with <a href="http://link/">extras</a>',
            module._safely_render_description(sub, extra_vars));
    },

}));

/**
 * Test for get_direct_description_node() method.
 */
suite.add(new Y.Test.Case({
    name: 'Test direct node construction with appropriate description.',

    test_no_subscriptions: function() {
        // A description is added in even when there are no subscriptions.
        var info = {
            direct: _constructCategory(),
            count: 0
        };
        var expected_text = module._get_direct_subscription_information(info);
        var node = module._get_direct_description_node(info);
        Y.Assert.areEqual(
            'direct-subscription', node.get('id'));
        Y.Assert.areEqual(
            expected_text, node.get('text'));
    },

    test_direct_subscription: function() {
        // One personal, direct subscription exists.
        var info = {
            direct: _constructCategory([{ bug: {} }]),
            count: 1
        };
        var expected_text = module._get_direct_subscription_information(info);
        var node = module._get_direct_description_node(info);
        Y.Assert.areEqual(
            'direct-subscription', node.get('id'));
        Y.Assert.areEqual(
            expected_text, node.get('text'));
    },

}));

/**
 * Test for get_single_description_node() method.
 */
suite.add(new Y.Test.Case({
    name: 'Test single subscription description node construction.',

    test_simple_text: function() {
        // A simple subscription with 'Text' as the reason and no variables.
        var sub = { reason: 'Text', vars: {}, action: function() {} };
        var node = module._get_single_description_node(sub);

        // The node has appropriate CSS class set.
        Y.Assert.isTrue(node.hasClass('subscription-description'));

        // There is also a sub-node containing the actual description.
        var subnode = node.one('.description-text');
        Y.Assert.areEqual('Text', subnode.get('text'));
    },

    test_variable_substitution: function() {
        // A subscription with variables and extra variables
        // has them replaced.
        var sub = { reason: 'Test {var1} {var2}',
                    vars: { var1: 'my text'},
                    action: function() {} };
        var extra_data = { var2: 'globally' };
        var node = module._get_single_description_node(sub, extra_data);

        // The node has appropriate CSS class set.
        Y.Assert.isTrue(node.hasClass('subscription-description'));

        // There is also a sub-node containing the actual description.
        var subnode = node.one('.description-text');
        Y.Assert.areEqual('Test my text globally', subnode.get('text'));
    },

}));

/**
 * Test for get_other_descriptions_node() method.
 */
suite.add(new Y.Test.Case({
    name: 'Test creation of node describing all non-direct subscriptions.',

    test_no_subscriptions: function() {
        // With just a personal subscription, undefined is returned.
        var info = {
            direct: _constructCategory([{ bug: {} }]),
            from_duplicate: _constructCategory(),
            as_assignee: _constructCategory(),
            as_owner: _constructCategory(),
            count: 1
        };
        window.LP = { cache: {} };
        Y.Assert.areSame(
            undefined,
            module._get_other_descriptions_node(info));
        delete window.LP;
    },

    test_one_subscription: function() {
        // There is a subscription on the duplicate bug.
        var info = {
            direct: _constructCategory(),
            from_duplicate: _constructCategory([{ bug: {id: 1} }]),
            as_assignee: _constructCategory(),
            as_owner: _constructCategory(),
            count: 1
        };
        window.LP = { links: { me: '~' } };

        // A node is returned with ID of 'other-subscriptions'.
        var node = module._get_other_descriptions_node(info);
        Y.Assert.areEqual(
            'other-subscriptions', node.get('id'));
        // And it contains single '.subscription-description' node.
        Y.Assert.areEqual(
            1, node.all('.subscription-description').size());
        delete window.LP;
    },

    test_multiple_subscription: function() {
        // There is a subscription on the duplicate bug 1,
        // and another as assignee on bug 2.
        var info = {
            direct: _constructCategory(),
            from_duplicate: _constructCategory([{ bug: {id: 1} }]),
            as_assignee: _constructCategory([{ bug: {id: 2} }]),
            as_owner: _constructCategory(),
            count: 1
        };
        window.LP = { cache: { context: { web_link: '/' } },
                      links: { me: '~' } };

        // A node is returned containing two
        // '.subscription-description' nodes.
        var node = module._get_other_descriptions_node(info);
        Y.Assert.areEqual(
            2, node.all('.subscription-description').size());
        delete window.LP;
    },

    test_no_direct_has_structural_subscriptions: function() {
        // With no non-personal subscriptions, and a structural
        // subscription, the node is still constructed because
        // structural subscriptions go there as well.
        var info = {
            direct: _constructCategory([{ bug: {} }]),
            from_duplicate: _constructCategory(),
            as_assignee: _constructCategory(),
            as_owner: _constructCategory(),
            count: 1
        };
        window.LP = { cache: { subscription_info: ['1'] } };
        Y.Assert.isNotUndefined(
            module._get_other_descriptions_node(info));
        delete window.LP;
    },

    test_header: function() {
        // There is a subscription on the duplicate bug.
        var info = {
            direct: _constructCategory(),
            from_duplicate: _constructCategory([{ bug: {id: 1} }]),
            as_assignee: _constructCategory(),
            as_owner: _constructCategory(),
            count: 1
        };

        window.LP = { links: { me: '~' } };

        // A returned node contains the 'other-subscriptions-header'
        // div with the link.
        var node = module._get_other_descriptions_node(info);
        var header = node.one('#other-subscriptions-header');
        Y.Assert.isNotUndefined(header);
        var link = header.one('a');
        Y.Assert.areEqual('Other subscriptions', link.get('text'));

        delete window.LP;
    },

    test_header_slideout: function() {
        // Clicking on the header slides-out the box, and
        // clicking it again slides it back in.
        var info = {
            direct: _constructCategory(),
            from_duplicate: _constructCategory([{ bug: {id: 1} }]),
            as_assignee: _constructCategory(),
            as_owner: _constructCategory(),
            count: 1
        };

        window.LP = { links: { me: '~' } };

        // A returned node contains the 'other-subscriptions-header'
        // div with the link.
        var node = module._get_other_descriptions_node(info);
        var link = node.one('#other-subscriptions-header a');
        var list = node.one('#other-subscriptions-list');

        // Initially, the list is hidden.
        Y.Assert.isTrue(link.hasClass('treeCollapsed'));
        Y.Assert.isTrue(list.hasClass('lazr-closed'));
        Y.Assert.areEqual('none', list.getStyle('display'));

        // Clicking the link slides out the list of other subscriptions.
        Y.Event.simulate(Y.Node.getDOMNode(link), 'click');
        this.wait(function() {
            Y.Assert.isFalse(link.hasClass('treeCollapsed'));
            Y.Assert.isTrue(link.hasClass('treeExpanded'));
            Y.Assert.isFalse(list.hasClass('lazr-closed'));
            Y.Assert.areNotEqual('none', list.getStyle('display'));

            // Clicking it again, slides it back in.
            // It has to be nested inside 'wait' because we need
            // to wait for the first click to "finish".
            Y.Event.simulate(Y.Node.getDOMNode(link), 'click');

            this.wait(function() {
                Y.Assert.isTrue(link.hasClass('treeCollapsed'));
                Y.Assert.isFalse(link.hasClass('treeExpanded'));
                Y.Assert.isTrue(list.hasClass('lazr-closed'));
                delete window.LP;
            }, 500);
        }, 500);
    },

}));

/**
 * Test for show_subscription_description() method.
 */
suite.add(new Y.Test.Case({
    name: 'Test showing of subscription descriptions.',

    setUp: function() {
        this.content_node = Y.Node.create('<div></div>')
            .set('id', 'description-container');
        this.parent_node = Y.one('#test-root');
        this.parent_node.appendChild(this.content_node);
        this.config = {
            description_box: '#description-container',
        };
    },

    tearDown: function() {
        this.parent_node.empty(true);
        delete this.config;
    },

    test_no_subscriptions: function() {
        // With no subscriptions, a simple description of that state
        // is added.
        this.config.subscription_info = {
            direct: _constructCategory(),
            from_duplicate: _constructCategory(),
            as_assignee: _constructCategory(),
            as_owner: _constructCategory(),
            bug_id: 1,
            count: 0
        };
        window.LP = { cache: {} };
        module.show_subscription_description(this.config);
        this.wait(function() {
            Y.Assert.areEqual(
                1, this.content_node.all('#direct-subscription').size());
            Y.Assert.areEqual(
                0, this.content_node.all('#other-subscriptions').size());
        }, 50);
        delete window.LP;
    },

    test_combined_subscriptions: function() {
        // With both direct and implicit subscriptions,
        // we get a simple description and a node with other descriptions.
        this.config.subscription_info = {
            direct: _constructCategory([{ bug: {id:1} }]),
            from_duplicate: _constructCategory([{ bug: {id:2} }]),
            as_assignee: _constructCategory([{ bug: {id:3} }]),
            as_owner: _constructCategory(),
            bug_id: 1,
            count: 0
        };
        window.LP = { cache: { context: { web_link: '/' } },
                      links: { me: '~' } };
        module.show_subscription_description(this.config);
        this.wait(function() {
            Y.Assert.areEqual(
                1, this.content_node.all('#direct-subscription').size());
            Y.Assert.areEqual(
                1, this.content_node.all('#other-subscriptions').size());
            delete window.LP;
        }, 50);
    },

    test_reference_substitutions: function() {
        // References of the form `subscription-cache-reference-*` get
        // replaced with LP.cache[...] values.
        this.config.subscription_info = {
            reference: 'subscription-cache-reference-X',
            direct: _constructCategory(),
            from_duplicate: _constructCategory(),
            as_assignee: _constructCategory(),
            as_owner: _constructCategory(),
            bug_id: 1,
            count: 0
        };
        window.LP = {
            cache: {
                'subscription-cache-reference-X': 'value'
            }
        };
        module.show_subscription_description(this.config);
        Y.Assert.areEqual(
            'value',
            this.config.subscription_info.reference);
        delete window.LP;
    },

}));

/**
 * Test for actions node construction.
 */
suite.add(new Y.Test.Case({
    name: 'Test node construction for actions.',

    test_change_assignees: function() {
        window.LP = { cache: { context: { web_link: 'http://test/' } } };
        var link = module._actions.CHANGE_ASSIGNEES();
        Y.Assert.areEqual('Change assignees for this bug', link.get('text'));
        Y.Assert.areEqual('http://test/', link.get('href'));
        delete window.LP;
    },

}));

var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});

