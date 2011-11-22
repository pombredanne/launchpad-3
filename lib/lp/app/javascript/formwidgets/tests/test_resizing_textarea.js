/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'node', 'event',
          'node-event-simulate', 'event-valuechange', 'plugin',
          'lp.app.formwidgets.resizing_textarea', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var test_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecenas ut viverra nibh. Morbi sit amet tellus accumsan justo rutrum blandit sit amet ac augue. Pellentesque eget diam at purus suscipit venenatis. Proin non neque lacus. Curabitur venenatis tempus sem, vitae porttitor magna fringilla vel. Cras dignissim egestas lacus nec hendrerit. Proin pharetra, felis ac auctor dapibus, neque orci commodo lorem, sit amet posuere erat quam euismod arcu. Nulla pharetra augue at enim tempus faucibus. Sed dictum tristique nisl sed rhoncus. Etiam tristique nisl eget risus blandit iaculis. Lorem ipsum dolor sit amet, consectetur adipiscing elit.";

/**
 * Helper function to turn the string from getComputedStyle to int
 *
 */
function clean_size(val) {
    return parseInt(val.replace('px', ''), 10);
}

/**
 * In order to update the content we need to change the text, but also to fire
 * the event that the content has changed since we're modifying it
 * programatically
 *
 */
function update_content(target, val) {
    console.log(target);
    target.set('value', val);
    target.simulate('valueChange');
}


var suite = new Y.Test.Suite("Resizing Textarea Tests");

suite.add(new Y.Test.Case({

    name: 'resizing_textarea',

    setUp: function() {},

    tearDown: function() {},

    test_initial_resizable: function() {
        var target = Y.one('#init');
            trim = Y.Lang.trim;

        Assert.areEqual('Initial text', target.get('value'));

        target.plug(Y.lp.app.formwidgets.ResizingTextarea);

        // get the current sizes so we can pump text into it and make sure it
        // grows
        var orig_width = clean_size(target.getComputedStyle('width'));
            orig_height = clean_size(target.getComputedStyle('height'));

        console.log(orig_width, orig_height);

        update_content(target, test_text);

        var new_width = clean_size(target.getComputedStyle('width'));
            new_height = clean_size(target.getComputedStyle('height'));

        console.log('new height', new_width, new_height);

        Assert.isTrue(new_height > orig_height,
            "The height should increase with content");
    },

}));

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function (e) {
    Y.lp.testing.Runner.run(suite);
});

});
