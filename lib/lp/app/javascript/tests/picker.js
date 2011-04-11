/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use('test', 'console', 'node', 'lp', 'lp.client', 'escape', 'lazr.picker',
        'lp.app.picker', 'event', 'event-focus', 'event-simulate',
        function(Y) {

var Assert = Y.Assert;
            
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
        bb.get('parentNode').removeChild(bb);
    }
    // Kill the widget itself.
    widget.destroy();
}

var suite = new Y.Test.Suite("Launchpad Picker Tests");

/*
 * Test cases for a picker with a yesno validation callback.
 */
suite.add(new Y.Test.Case({

    name: 'picker_yesyno_validation',

    setUp: function() {
        this.vocabulary = [
            {"value": "fred", "title": "Fred", "css": "sprite-person",
                "description": "fred@example.com", "api_uri": "~/fred"},
            {"value": "frieda", "title": "Frieda", "css": "sprite-person",
                "description": "frieda@example.com", "api_uri": "~/frieda"}
        ];
    },

    tearDown: function() {
        cleanup_widget(this.picker);
    },

    create_picker: function(validate_callback) {
        this.picker = Y.lp.app.picker.addPickerPatcher(
            this.vocabulary,
            "foo/bar",
            "test_link",
            "picker_id",
            {"step_title": "Choose someone",
             "header": "Pick Someone",
             "remove_button_text": "Remove someone",
             "null_display_value": "Noone",
             "show_remove_button": true,
             "show_assign_me_button": true,
             "validate_callback": validate_callback});
    },

    test_picker_can_be_instantiated: function() {
        // Ensure the picker can be instantiated.
        this.create_picker();
        Assert.isInstanceOf(
            Y.lazr.Picker, this.picker, "Picker failed to be instantiated");
    },

    // Called when the picker saves it's data. Sets a flag for checking.
    picker_save_callback: function(save_flag) {
        return function(e) {
            save_flag.event_has_fired = true;
        }
    },

    // A validation callback stub. Instead of going to the server to see if
    // a picker value requires confirmation, we compare it to a known value.
    yesno_validate_callback: function(save_flag, expected_value) {
        var save_fn = this.picker_save_callback(save_flag);
        return function(picker, value, ignore, cancelFn) {
            Assert.areEqual(
                    expected_value, value.api_uri, "unexpected picker value");
            if (value == null)
                return true;
            var requires_confirmation = value.api_uri != "~/fred";
            if (requires_confirmation) {
                var yesno_content = "<p>Confirm selection</p>";
                return Y.lp.app.picker.yesno_save_confirmation(
                        picker, yesno_content, save_fn, cancelFn);
            } else {
                save_fn();
            }
            return True;
        }
    },

    test_no_confirmation_required: function() {
        // Test that the picker saves the selected value if no confirmation
        // is required.
        var save_flag = {};
        this.create_picker(this.yesno_validate_callback(save_flag, "~/fred"));
        this.picker.set('results', this.vocabulary);
        this.picker.render();

        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(1)', 'click');
        Assert.isTrue(save_flag.event_has_fired, "save event wasn't fired.");
    },

    test_validation_yes: function() {
        // Test that the picker saves the selected value if the user answers
        // "Yes" to a confirmation request.
        var save_flag = {};
        this.create_picker(
                this.yesno_validate_callback(save_flag, "~/frieda"));
        this.picker.set('results', this.vocabulary);
        this.picker.render();

        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(2)', 'click');
        // We need to wait for the animation eye candy to finish.
        this.wait(function() {
            var yesno = this.picker.get('contentBox').one('.yesyno_buttons');
            simulate(
                    yesno, 'button:nth-child(1)', 'click');
            Assert.isTrue(
                    save_flag.event_has_fired, "save event wasn't fired.");
        }, 400);
    },

    test_validation_no: function() {
        // Test that the picker doesn't save the selected value if the answers
        // "No" to a confirmation request.
        var save_flag = {};
        this.create_picker(
                this.yesno_validate_callback(save_flag, "~/frieda"));
        this.picker.set('results', this.vocabulary);
        this.picker.render();

        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(2)', 'click');
        // We need to wait for the animation eye candy to finish.
        this.wait(function() {
            var yesno = this.picker.get('contentBox').one('.yesyno_buttons');
            simulate(
                    yesno, 'button:nth-child(2)', 'click');
            Assert.areEqual(
                    undefined, save_flag.event_has_fired,
                    "save event wasn't fired.");
        }, 400);
    }
}));

// Lock, stock, and two smoking barrels.
var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var yui_console = new Y.Console({
    newestOnTop: false
});
yui_console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
