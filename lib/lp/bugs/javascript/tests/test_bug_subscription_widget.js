/* Copyright (c) 2010, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false
    }).use(
        'event', 'lp.bugs.bug_subscription_widget', 'node', 'test',
        'widget-stack', 'console', function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var rawnode = Y.Node.getDOMNode(widget.one(selector));
    Y.Event.simulate(rawnode, evtype, options);
}

/* Helper function to clean up a dynamically added widget instance. */
function cleanup_widget(widget) {
    // Nuke the boundingBox, but only if we've touched the DOM.
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        if (bb.get('parentNode')) {
            bb.get('parentNode').removeChild(bb);
        }
    }
    // Kill the widget itself.
    widget.destroy();
}

var suite = new Y.Test.Suite("Bug subscription widget tests");

suite.add(new Y.Test.Case({

    name: 'bug_subscription_widget_basics',

    setUp: function() {
        // Monkeypatch LP.client to avoid network traffic and to make
        // some things work as expected.
        LP.client.Launchpad.prototype.named_post =
            function(url, func, config) {
                config.on.success();
            };
        LP.client.cache.bug = {
            self_link: "http://bugs.example.com/bugs/1234"
        };
        this.subscribe_overlay =
            Y.lp.bugs.bug_subscription_widget.create_subscription_overlay();
        this.subscribe_overlay.show();
    },

    test_bug_notification_level_values: function() {
        // The bug_notification_level field will have a value that's one
        // of [Discussion, Details, Lifecycle].
        var form_node = this.subscribe_overlay.form_node;
        var notification_level_radio_buttons = form_node.queryAll(
            'input[name=field.bug_notification_level]');
        Y.each(notification_level_radio_buttons, function(obj) {
            var value = obj.getAttribute('value');
            Assert.isTrue(
                value == 'Discussion' ||
                value == 'Details' ||
                value == 'Lifecycle');
        });
    }

}));

var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.get('body').appendChild(status_node);
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
