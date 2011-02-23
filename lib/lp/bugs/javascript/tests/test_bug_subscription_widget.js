/* Copyright (c) 2010, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false,
    }).use(
        'event', 'event-simulate', 'lazr.testing.mockio',
        'lp.bugs.bug_subscription_wizard', 'lp.client', 'node', 'test',
        'widget-stack', 'console', 'log', function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;

var suite = new Y.Test.Suite("Bug subscription widget tests");
var subscribe_node = Y.Node.create(
    '<a href="#" id="subscription-widget-link">Click me</a>');

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
var success_response = Y.lazr.testing.MockIo.makeXhrSuccessResponse(
    subscribe_form_body);
var mock_io = new Y.lazr.testing.MockIo();

suite.add(new Y.Test.Case({

    name: 'bug_subscription_wizard_basics',

    setUp: function() {
        // Monkeypatch LP.client to avoid network traffic and to make
        // some things work as expected.
        window.LP = {
            client: {
                links: {},
                cache: {}
            }
        };
        LP.cache.bug = {
            self_link: "http://bugs.example.com/bugs/1234"
        };
        Y.lp.client.Launchpad = function() {}
                // Empty client constructor.
        Y.lp.client.Launchpad.prototype.named_post =
          function(url, func, config) {
            config.on.success();
          };

        // Monkeypatch the subscribe_form_body attribute of the
        // wizard module so that the test doesn't cause the wizard to
        // try to load a Launchpad page.
        Y.lp.bugs.bug_subscription_wizard.subscribe_form_body =
            subscribe_form_body;
        Y.lp.bugs.bug_subscription_wizard.create_subscription_wizard();
        this.subscription_wizard =
            Y.lp.bugs.bug_subscription_wizard.subscription_wizard;
    },

    tearDown: function() {
        this.subscription_wizard.destroy();
    },

    test_bug_notification_level_values: function() {
        // The bug_notification_level field will have a value that's one
        // of [Discussion, Details, Lifecycle].
        var form_node = this.subscription_wizard.form_node;
        var notification_level_radio_buttons = form_node.all(
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
        var steps = this.subscription_wizard.steps;
        Assert.areEqual(
            subscribe_form_body,
            this.subscription_wizard.get('steps')[0].get('form_content'));
    },

    test_wizard_is_hidden_on_creation: function() {
        // The wizard is hidden when it is created.
        var bounding_box =
            this.subscription_wizard.get('boundingBox');
        Assert.isFalse(this.subscription_wizard.get('visible'));
        Assert.isTrue(
            bounding_box.hasClass('yui3-lazr-wizard-hidden'),
            "The form is hidden after cancel is clicked.");
    }
}));


suite.add(new Y.Test.Case({

    name: 'bug_subscription_wizard_async',

    setUp: function() {
        // Monkeypatch LP.client to avoid network traffic and to make
        // some things work as expected.
        window.LP = {
            client: {
                links: {},
                cache: {}
            }
        };
        Y.lp.client.Launchpad = function() {}
        Y.lp.client.Launchpad.prototype.named_post =
          function(url, func, config) {
            config.on.success();
          };
        LP.cache.bug = {
            self_link: "http://bugs.example.com/bugs/1234"
        };

        // Monkeypatch the subscribe_form_body attribute of the
        // wizard module so that the test doesn't cause the wizard to
        // try to load a Launchpad page.
        Y.lp.bugs.bug_subscription_wizard.subscribe_form_body =
            subscribe_form_body;
    },

    tearDown: function() {
        Y.lp.bugs.bug_subscription_wizard.subscription_wizard.destroy();
    },

    test_create_subscription_wizard_fires_event: function() {
        // The create_subscription_wizard function fires a
        // subscriptionwizard:ready event when it has completed so that
        // the subscription wizard can then be used in a page.
        var subscriptionwizard_ready_fired = false;
        Y.on(
            'subscriptionwizard:ready',
            Y.bind(function(e) { subscriptionwizard_ready_fired = true; }));
        Y.lp.bugs.bug_subscription_wizard.create_subscription_wizard();
        Assert.isTrue(subscriptionwizard_ready_fired);
    },

    test_load_subscription_form_fires_event: function() {
        // The load_subscription_form() function fires a
        // subscriptionform:loaded event.
        var subscriptionform_loaded_fired = false;
        Y.on(
            'subscriptionform:loaded',
            Y.bind(function(e) { subscriptionform_loaded_fired = true; }));
        Y.lp.bugs.bug_subscription_wizard.load_subscription_form(
            'http://example.com', mock_io);
        mock_io.simulateXhr(success_response, false);
        Assert.isTrue(subscriptionform_loaded_fired);
    },

    test_wizard_created_on_subscriptionform_loaded_event: function() {
        // When the subscriptionform:loaded event is fired, the wizard
        // will be created.
        Y.lp.bugs.bug_subscription_wizard.set_up_event_handlers(
            subscribe_node);
        Y.fire('subscriptionform:loaded');
        var subscription_wizard =
            Y.lp.bugs.bug_subscription_wizard.subscription_wizard;
        Assert.areEqual(
            subscribe_form_body,
            subscription_wizard.get('steps')[0].get('form_content'))
    },

    test_load_subscription_form_loads_subscription_form: function() {
        // The load_subscription_form() function loads the body of the
        // subscription form form a remote URL.
        Y.lp.bugs.bug_subscription_wizard.set_up_event_handlers(
            subscribe_node);
        Y.lp.bugs.bug_subscription_wizard.load_subscription_form(
            'http://example.com', mock_io);
        mock_io.simulateXhr(success_response, false);

        // The contents of the subscribe_form_body for the wizard will
        // have been loaded.
        var subscription_wizard =
            Y.lp.bugs.bug_subscription_wizard.subscription_wizard;
        Assert.areEqual(
            subscribe_form_body,
            subscription_wizard.get('steps')[0].get('form_content'));
    },

    test_initialize_subscription_wizard_links_everything: function() {
        // The initialize_subscription_wizard function sets up event
        // handlers and links the wizard, once created, to the node that
        // we pass to it.
        var subscriptionform_loaded_fired = false;
        var subscriptionwizard_ready_fired = false;
        Y.on(
            'subscriptionform:loaded',
            Y.bind(function(e) { subscriptionform_loaded_fired = true; }));
        Y.on(
            'subscriptionwizard:ready',
            Y.bind(function(e) { subscriptionwizard_ready_fired = true; }));
        Y.lp.bugs.bug_subscription_wizard.initialize_subscription_wizard(
            subscribe_node, 'http://example.com', mock_io);
        mock_io.simulateXhr(success_response, false);
        Y.Event.simulate(Y.Node.getDOMNode(subscribe_node), 'click');

        // All the events will have fired and the node will be linked to
        // the wizard via its onClick handler.
        var subscription_wizard =
            Y.lp.bugs.bug_subscription_wizard.subscription_wizard;
        Assert.isTrue(subscriptionform_loaded_fired);
        Assert.isTrue(subscriptionwizard_ready_fired);
        Assert.areEqual(
            subscribe_form_body,
            subscription_wizard.get('steps')[0].get('form_content'));
        Assert.isTrue(subscription_wizard.get('visible'));
    },

    test_submitting_wizard_form_fires_event: function() {
        // When the wizard form is submitted, a
        // subscriptionwizard:save event is fired.
        var subscriptionwizard_save_fired = false;
        Y.on(
            'subscriptionwizard:save',
            Y.bind(function(e) { subscriptionwizard_save_fired = true; }));
        Y.on(
            'subscriptionwizard:ready',
            Y.bind(function(e) {
                var subscription_wizard =
                    Y.lp.bugs.bug_subscription_wizard.subscription_wizard;
                var submit_button =
                    Y.one('input[type=submit]');
                Y.Event.simulate(Y.Node.getDOMNode(submit_button), 'click');
            }));

        Y.lp.bugs.bug_subscription_wizard.initialize_subscription_wizard(
            subscribe_node, 'http://example.com', mock_io);
        mock_io.simulateXhr(success_response, false);
        Y.lp.bugs.bug_subscription_wizard.show_wizard();
        Assert.isTrue(subscriptionwizard_save_fired);
    }
}));


var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
