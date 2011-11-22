/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'node',
           'event', 'event-simulate', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(selector, evtype) {
    var rawnode = Y.Node.getDOMNode(Y.one(selector));
    Y.Event.simulate(rawnode, evtype);
}

/* Helper function to clean up a dynamically added widget instance. */
function cleanup_widget(widget) {
    // Nuke the boundingBox, but only if we've touched the DOM.
    if (widget.get('rendered')) {
        var bb = widget.get('boundingBox');
        bb.get('parentNode').removeChild(bb);
    }
    // Kill the widget itself.
    widget.destroy();
}

var suite = new Y.Test.Suite("TextExpander Tests");


suite.add(new Y.Test.Case({

    name: 'text_expander',

    setUp: function() {
        // this.workspace = Y.one('#workspace');
        // if (!this.workspace){
        //     Y.one(document.body).appendChild(Y.Node.create(
        //         '<div id="workspace" ' +
        //         'style="border: 1px solid blue; ' +
        //         'width: 20em; ' +
        //         'margin: 1em; ' +
        //         'padding: 1em">'+
        //         '</div>'));
        //     this.workspace = Y.one('#workspace');
        // }
        // this.workspace.appendChild(Y.Node.create(
        //     '<div id="example-1">' +
        //     '<div id="custom-animation-node"/>' +
        //     '<span class="yui3-activator-data-box">' +
        //     '    Original Value' +
        //     '</span>' +
        //     '<button ' +
        //     ' class="lazr-btn yui3-activator-act yui3-activator-hidden">' +
        //     '    Go' +
        //     '</button>' +
        //     '<div class="yui3-activator-message-box yui3-activator-hidden">' +
        //     '</div>' +
        //     '</div>'));
        // this.activator = new Y.lazr.activator.Activator(
        //     {contentBox: Y.one('#example-1')});
        // this.action_button = this.activator.get('contentBox').one(
        //     '.yui3-activator-act');
    },

    tearDown: function() {
        // cleanup_widget(this.activator);
        // this.workspace.set('innerHTML', '');
    },

    test_correct_animation_node: function() {
        // Check that the correct animation node is used.
        // First check the default.
        Assert.areEqual(this.activator.get('contentBox'),
                    this.activator.animation_node);
        // Now check a custom one.
        var custom_node = Y.one('#custom-animation-node');
        this.activator = new Y.lazr.activator.Activator(
            {contentBox: Y.one('#example-1'), animationNode: custom_node});
        Assert.areEqual(custom_node, this.activator.animation_node);
    },

}));

Y.lp.testing.Runner.run(suite);

});
