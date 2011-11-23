/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'node', 'event',
          'node-event-simulate', 'event-valuechange', 'plugin',
          'lp.app.formwidgets.resizing_textarea', function(Y) {

var Assert = Y.Assert,  // For easy access to isTrue(), etc.
    CHANGE_TIME = 100;    // we need a slight delay for the reize to happen

var test_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecenas ut viverra nibh. Morbi sit amet tellus accumsan justo rutrum blandit sit amet ac augue. Pellentesque eget diam at purus suscipit venenatis. Proin non neque lacus. Curabitur venenatis tempus sem, vitae porttitor magna fringilla vel. Cras dignissim egestas lacus nec hendrerit. Proin pharetra, felis ac auctor dapibus, neque orci commodo lorem, sit amet posuere erat quam euismod arcu. Nulla pharetra augue at enim tempus faucibus. Sed dictum tristique nisl sed rhoncus. Etiam tristique nisl eget risus blandit iaculis. Lorem ipsum dolor sit amet, consectetur adipiscing elit.";

/**
 * Helper function to turn the string from getComputedStyle to int
 *
 */
function clean_size(val) {
    return parseInt(val.replace('px', ''), 10);
}

/**
 * Helper to extract the computed height of the element
 *
 */
function get_height(target) {
    return clean_size(target.getComputedStyle('height'));
}

/**
 * In order to update the content we need to change the text, but also to fire
 * the event that the content has changed since we're modifying it
 * programatically
 *
 */
function update_content(target, val) {
    target.set('value', val);
    target.simulate('keydown', {keycode: 97});
    target.simulate('keyup', {keycode: 97});
}

/**
 * When the box resizes, it needs a slight sec to make the change
 *
 * We need to pause and all tests should do this so we wrap it
 *
 */
function assert_change(callback) {
    setTimeout(callback, CHANGE_TIME);
}


var suite = new Y.Test.Suite("Resizing Textarea Tests");

suite.add(new Y.Test.Case({

    name: 'resizing_textarea',

    test_initial_resizable: function() {
        var target = Y.one('#init');

        Assert.areEqual('Initial text', target.get('value'));

        target.plug(Y.lp.app.formwidgets.ResizingTextarea, {
            skip_animations: true
        });

        // get the current sizes so we can pump text into it and make sure it
        // grows
        var orig_height = get_height(target);
        update_content(target, test_text);

        // we have to wait for the resize
        this.wait(function () {
            var new_height = get_height(target);
            Assert.isTrue(new_height > orig_height,
                "The height should increase with content");
        }, CHANGE_TIME);

    },

    test_max_height: function () {
        var target = Y.one('#with_defaults');

        target.plug(Y.lp.app.formwidgets.ResizingTextarea, {
            skip_animations: true,
            max_height: 200,
            min_height: 100
        }, CHANGE_TIME);

        this.wait(function () {
            var min_height = get_height(target);
            Assert.isTrue(min_height === 100,
                "The height should be no smaller than 100px");
        }, CHANGE_TIME);

        update_content(target, test_text);

        // we have to wait for the resize
        this.wait(function () {
            var new_height = get_height(target);
            Assert.isTrue(new_height === 200,
                "The height should only get to 200px");
        }, CHANGE_TIME);
    },

    test_removing_content: function () {
        var target = Y.one('#shrinkage');

        target.plug(Y.lp.app.formwidgets.ResizingTextarea, {
            skip_animations: true,
            min_height: 100
        });

        update_content(target, test_text);
        this.wait(function () {
            var max_height = get_height(target);
            Assert.isTrue(max_height > 100,
                "The height should be larger than our min with content");
        }, CHANGE_TIME);

        update_content(target, "shrink");

        this.wait(function () {
            var min_height = get_height(target);
            Assert.isTrue(min_height === 100,
                "The height should shrink back to our min");
        }, CHANGE_TIME);
    },

    test_multiple: function () {
        var target = Y.all('.test_multiple');

        target.plug(Y.lp.app.formwidgets.ResizingTextarea, {
            skip_animations: true,
            min_height: 100
        });

        this.wait(function () {
            target.each(function (n) {
                var min_height = get_height(n);
                Assert.isTrue(min_height === 100,
                    "The height of the node should be 100");
            });
        }, CHANGE_TIME);

        // now set the content in the first one and check it's unique
        update_content(Y.one('.first'), test_text);

        this.wait(function () {
            var first = Y.one('.first'),
                second = Y.one('.second');

            var first_height = get_height(first);
            Assert.isTrue(first_height > 100,
                "The height of the first should now be > 100");

            var second_height = get_height(second);
            Assert.isTrue(second === 100,
                "The height of the second should still be > 100");
        }, CHANGE_TIME);
    }
}));

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function (e) {
    Y.lp.testing.Runner.run(suite);
});

});
