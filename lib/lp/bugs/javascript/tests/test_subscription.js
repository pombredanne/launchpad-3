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
 * Gather short (just-enough) subscription records for all assignments.
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

