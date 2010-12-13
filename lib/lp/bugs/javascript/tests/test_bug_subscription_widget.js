/* Copyright (c) 2010, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use(
        'event', 'lp.bugs.bug_subscription_wizard', 'node', 'test',
        'widget-stack', 'console', 'log', function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;

var suite = new Y.Test.Suite("Bug subscription widget tests");

var subscribe_form_body =
    '<div>' +
    '    <p>Tell me when</p>' +
    '    <table>' +
    '       <tr>' +
    '         <td>' +
    '           <input type="radio" ' +
    '               name="field.bug_notification_level" ' +
    '               id="bug-notification-level-comments"' +
    '               value="Discussion"' +
    '               class="bug-notification-level" />' +
    '         </td>' +
    '         <td>' +
    '           <label for="bug-notification-level-comments">' +
    '             A change is made or a comment is added to ' + 
    '             this bug' +
    '           </label>' +
    '         </td>' +
    '     </tr>' +
    '     <tr>' +
    '       <td>' +
    '         <input type="radio"' +
    '             name="field.bug_notification_level" ' +
    '             id="bug-notification-level-metadata"' +
    '             value="Details"' +
    '             class="bug-notification-level" />' +
    '       </td>' +
    '       <td>' +
    '         <label for="bug-notification-level-metadata">' +
    '             A change is made to the bug; do not notify ' +
    '             me about new comments.' +
    '         </label>' +
    '       </td>' +
    '     </tr>' +
    '     <tr>' +
    '       <td>' +
    '         <input type="radio"' +
    '             name="field.bug_notification_level" ' +
    '             id="bug-notifiction-level-lifecycle"' +
    '             value="Lifecycle"' +
    '             class="bug-notification-level" />' +
    '       </td>' +
    '       <td>' +
    '         <label for="bug-notification-level-lifecycle">' +
    '           Changes are made to the bug\'s status.' +
    '         </label>' +
    '       </td>' +
    '     </tr>' +
    '  </table>' +
    '</div>';

suite.add(new Y.Test.Case({

    name: 'bug_subscription_wizard_basics',

    setUp: function() {
        // Monkeypatch LP.client to avoid network traffic and to make
        // some things work as expected.
        window.LP = {
            client: {
                links: {},
                // Empty client constructor.
                Launchpad: function() {},
                cache: {}
            }
        };
        LP.client.Launchpad.prototype.named_post =
            function(url, func, config) {
                config.on.success();
            };
        LP.client.cache.bug = {
            self_link: "http://bugs.example.com/bugs/1234"
        };

        // Monkeypatch the subscribe_form_body attribute of the
        // wizard module so that the test doesn't cause the wizard to
        // try to load a Launchpad page.
        Y.lp.bugs.bug_subscription_wizard.subscribe_form_body = 
            subscribe_form_body;
        Y.lp.bugs.bug_subscription_wizard.create_subscription_wizard();
        this.subscribe_wizard =
            Y.lp.bugs.bug_subscription_wizard.subscription_wizard;
    },

    test_bug_notification_level_values: function() {
        // The bug_notification_level field will have a value that's one
        // of [Discussion, Details, Lifecycle].
        var form_node = this.subscribe_wizard.form_node;
        var notification_level_radio_buttons = form_node.queryAll(
            'input[name=field.bug_notification_level]');
        Y.each(notification_level_radio_buttons, function(obj) {
            var value = obj.getAttribute('value');
            Assert.isTrue(
                value == 'Discussion' ||
                value == 'Details' ||
                value == 'Lifecycle');
        });
    },

    test_wizard_first_step_content: function() {
        // The form content for the first wizard step will have been
        // loaded using the _get_subscribe_form_content function defined
        // above.
        var steps = this.subscribe_wizard.steps;
        Assert.areEqual(
            subscribe_form_body,
            this.subscribe_wizard.get('steps')[0].get('form_content'));
    },

    test_wizard_created_on_subscriptionform_loaded_event: function() {
        // When the subscriptionform:loaded event is fired, the wizard
        // will be created.
        // Clear out the existing subscription_wizard.
        Y.lp.bugs.bug_subscription_wizard.initialize_subscription_wizard();
        Y.lp.bugs.bug_subscription_wizard.subscription_wizard = null;
        Y.fire('subscriptionform:loaded');
        var wizard =
            Y.lp.bugs.bug_subscription_wizard.subscription_wizard;
        Assert.areEqual(
            subscribe_form_body,
            wizard.get('steps')[0].get('form_content'))
    },

    test_create_subscription_wizad_fires_event: function() {
        // The create_subscription_wizard function fires a
        // subscriptionwizard:ready event when it has completed so that
        // the subscription wizard can then be used in a page.
        var subscriptionwizard_ready_fired = false;
        Y.on(
            'subscriptionwizard:ready',
            Y.bind(function(e) { subscriptionwizard_ready_fired = true; }));
        Y.lp.bugs.bug_subscription_wizard.create_subscription_wizard();
        Assert.isTrue(subscriptionwizard_ready_fired);
    }

}));

var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.get('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

//var yconsole = new Y.Console({
//    newestOnTop: false
//});
//yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
