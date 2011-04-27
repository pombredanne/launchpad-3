YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.bug_notification_level',
           'node-event-simulate',
           function(Y) {

var suite = new Y.Test.Suite("lp.bugs.bug_notification_level Tests");
var module = Y.lp.bugs.bug_notification_level;

/**
 * Test is_notification_level_shown() for a given set of
 * conditions.
 */
suite.add(new Y.Test.Case({
    name: 'Is the selection of notification levels shown',

    setUp: function () {
        this.MY_NAME = "ME";
        window.LP = { links: { me: "/~" + this.MY_NAME } };
    },

    tearDown: function() {
        delete window.LP;
    },

    test_subscribe_me: function() {
        // Person wants to subscribe so levels are shown:
        // the selected radio box has a value of the username,
        // and there is no option to update a subscription.
        Y.Assert.isTrue(
            module._is_notification_level_shown(this.MY_NAME, false));
    },

    test_unsubscribe_someone_else: function() {
        // Not subscribed (thus no option to update a subscription)
        // and wants to unsubscribe a team: levels are not shown.
        Y.Assert.isFalse(
            module._is_notification_level_shown('TEAM', false));
    },

    test_edit_subscription_me: function() {
        // There is either an existing subscription, or bug mail
        // is muted, so one can 'update existing subscription'.
        // If unmute/unsubscribe options are chosen, no level
        // options are shown.
        Y.Assert.isFalse(
            module._is_notification_level_shown(this.MY_NAME, true));
    },

    test_edit_subscription_update: function() {
        // There is either an existing subscription, or bug mail
        // is muted, so one can 'update existing subscription'.
        // If 'update-subscription' option is chosen, level
        // options are shown.
        Y.Assert.isTrue(
            module._is_notification_level_shown('update-subscription', true));
    },

    test_edit_subscription_someone_else: function() {
        // There is either an existing subscription, or bug mail
        // is muted, so one can 'update existing subscription'.
        // If unsubscribe a team option is chosen, no level
        // options are shown.
        Y.Assert.isFalse(
            module._is_notification_level_shown('TEAM', true));
    }

}));


/**
 * Test needs_toggling() which compares two sets of conditions and
 * returns if the need for notification level has changed.
 */
suite.add(new Y.Test.Case({
    name: 'State of the notification level visibility should change',

    setUp: function () {
        this.MY_NAME = "ME";
        window.LP = { links: { me: "/~" + this.MY_NAME } };
    },

    tearDown: function() {
        delete window.LP;
    },

    test_no_change: function() {
        // Both current_value and new_value are identical.
        Y.Assert.isFalse(
            module._needs_toggling('value', 'value', false));
        Y.Assert.isFalse(
            module._needs_toggling('value', 'value', true));
    },

    test_unsubscribe_to_team: function() {
        // Changing the option from 'unsubscribe me' (no levels shown)
        // to 'unsubscribe team' (no levels shown) means no change.
        Y.Assert.isFalse(
            module._needs_toggling(this.MY_NAME, 'TEAM', true));
    },

    test_edit_subscription_to_team: function() {
        // Changing the option from 'update-subscription' (levels shown)
        // to 'unsubscribe team' (no levels shown) means a change.
        Y.Assert.isTrue(
            module._needs_toggling('update-subscription', 'TEAM', true));
    }

}));


/**
 * Test toggle_field_visibility() which shows/hides a node based on
 * the value of bug_notification_level_visible value.
 */
suite.add(new Y.Test.Case({
    name: 'Toggle visibility of the notification levels with animations',

    test_quick_close: function() {
        // When quick_close===true, no animation happens and the
        // node is hidden.
        node = Y.Node.create('<div></div>');
        module._toggle_field_visibility(node, true);
        Y.Assert.isTrue(node.hasClass('lazr-closed'));
        Y.Assert.areEqual('none', node.getStyle('display'));
        Y.Assert.isFalse(module._bug_notification_level_visible);
        // Restore the default value.
        module._bug_notification_level_visible = true;
    },

    test_hide_node: function() {
        // Initially a node is shown, so 'toggling' makes it hidden.
        node = Y.Node.create('<div></div>');
        module._toggle_field_visibility(node);
        this.wait(function() {
            // Wait for the animation to complete.
            Y.Assert.isTrue(node.hasClass('lazr-closed'));
            Y.Assert.isFalse(module._bug_notification_level_visible);
        }, 500);
        // Restore the default value.
        module._bug_notification_level_visible = true;
    },

    test_show_node: function() {
        // When the node is closed, toggling shows it.
        module._bug_notification_level_visible = false;
        node = Y.Node.create('<div></div>');
        module._toggle_field_visibility(node);
        this.wait(function() {
            // Wait for the animation to complete.
            Y.Assert.isTrue(node.hasClass('lazr-opened'));
            Y.Assert.isTrue(module._bug_notification_level_visible);
        }, 500);
    },

    test_show_and_hide: function() {
        // Showing and then quickly hiding the node stops the
        // slide out animation for nicer rendering.
        module._bug_notification_level_visible = false;
        node = Y.Node.create('<div></div>');
        // This triggers the 'slide-out' animation.
        module._toggle_field_visibility(node);
        // Now we wait 100ms (<400ms for the animation) and
        // trigger the 'slide-in' animation.
        this.wait(function() {
            module._toggle_field_visibility(node);
            // The slide-out animation should be stopped now.
            Y.Assert.isFalse(module._slideout_animation.get('running'));
        }, 100);
        // Restore the default value.
        module._bug_notification_level_visible = true;
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
