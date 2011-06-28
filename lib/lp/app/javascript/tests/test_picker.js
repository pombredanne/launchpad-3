/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use('test', 'console', 'node', 'lp', 'lp.client', 'escape', 'event',
        'event-focus', 'event-simulate', 'lazr.picker', 'lp.app.widgets',
        'lp.app.picker', 'node-event-simulate',
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
    var data_box = Y.one('#picker_id .yui3-activator-data-box');
    var link = data_box.one('a');
    if (link) {
        link.get('parentNode').removeChild(link);
    }
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
        this.picker = null;
        this.text_input = null;
        this.select_menu = null;
    },

    tearDown: function() {
        if (this.select_menu !== null) {
            Y.one('body').removeChild(this.select_menu);
            }
        if (this.text_input !== null) {
            Y.one('body').removeChild(this.text_input);
            }
        if (this.picker !== null) {
            cleanup_widget(this.picker);
            }
    },

    create_picker: function(validate_callback) {
        this.picker = Y.lp.app.picker.addPickerPatcher(
            this.vocabulary,
            "foo/bar",
            "test_link",
            "picker_id",
            {
                "step_title": "Choose someone",
                "header": "Pick Someone",
                "null_display_value": "Noone",
                "show_remove_button": true,
                "show_assign_me_button": true,
                "validate_callback": validate_callback
            });
    },

    test_picker_can_be_instantiated: function() {
        // The picker can be instantiated.
        this.create_picker();
        Assert.isInstanceOf(
            Y.lp.app.widgets.Picker, this.picker,
            "Picker failed to be instantiated");
    },

    // Called when the picker saves it's data. Sets a flag for checking.
    picker_save_callback: function(save_flag) {
        return function(e) {
            save_flag.event_has_fired = true;
        };
    },

    // A validation callback stub. Instead of going to the server to see if
    // a picker value requires confirmation, we compare it to a known value.
    yesno_validate_callback: function(save_flag, expected_value) {
        var save_fn = this.picker_save_callback(save_flag);
        return function(picker, value, ignore, cancel_fn) {
            Assert.areEqual(
                    expected_value, value.api_uri, "unexpected picker value");
            if (value === null) {
                return true;
            }
            var requires_confirmation = value.api_uri !== "~/fred";
            if (requires_confirmation) {
                var yesno_content = "<p>Confirm selection</p>";
                Y.lp.app.picker.yesno_save_confirmation(
                        picker, yesno_content, "Yes", "No",
                        save_fn, cancel_fn);
            } else {
                save_fn();
            }
        };
    },

    test_no_confirmation_required: function() {
        // The picker saves the selected value if no confirmation
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

    test_TextFieldPickerPlugin_selected_item_is_saved: function () {
        // The picker saves the selected value to its associated
        // textfield if one is defined.
        this.text_input = Y.Node.create(
                '<input id="field.testfield" value="foo" />');
        node = Y.one(document.body).appendChild(this.text_input);
        this.create_picker();
        this.picker.plug(Y.lazr.TextFieldPickerPlugin,
                         {input_element: '[id="field.testfield"]'});
        this.picker.set('results', this.vocabulary);
        this.picker.render();
        var got_focus = false;
        this.text_input.on('focus', function(e) {
            got_focus = true;
        });
        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(1)', 'click');
        Assert.areEqual(
            'fred', Y.one('[id="field.testfield"]').get("value"));
        Assert.isTrue(got_focus, "focus didn't go to the search input.");
    },

    test_navigation_renders_after_results: function () {
        // We modify the base picker to show the batch navigation below the
        // picker results.
        this.create_picker();
        this.picker.set('results', this.vocabulary);
        var results_box = this.picker._results_box;
        var batch_box = this.picker._batches_box;
        Assert.areEqual(results_box.next(), batch_box);
    },

    test_confirmation_yes: function() {
        // The picker saves the selected value if the user answers
        // "Yes" to a confirmation request.
        var save_flag = {};
        this.create_picker(
                this.yesno_validate_callback(save_flag, "~/frieda"));
        this.picker.set('results', this.vocabulary);
        this.picker.render();

        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(2)', 'click');
        var yesno = this.picker.get('contentBox').one('.extra-form-buttons');

        simulate(
                yesno, 'button:nth-child(1)', 'click');
        Assert.isTrue(
                save_flag.event_has_fired, "save event wasn't fired.");
    },

    test_confirmation_no: function() {
        // The picker doesn't save the selected value if the answers
        // "No" to a confirmation request.
        var save_flag = {};
        this.create_picker(
                this.yesno_validate_callback(save_flag, "~/frieda"));
        this.picker.set('results', this.vocabulary);
        this.picker.render();

        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(2)', 'click');
        var yesno = this.picker.get('contentBox').one('.extra-form-buttons');
        simulate(
                yesno, 'button:nth-child(2)', 'click');
        Assert.areEqual(
                undefined, save_flag.event_has_fired,
                "save event wasn't fired.");
    },

    test_connect_select_menu: function() {
        // connect_select_menu() connects the select menu's onchange event to
        // copy the selected value to the text input field.
        this.text_input = Y.Node.create(
                '<input id="field.testfield" value="foo" />');
        var node = Y.one(document.body).appendChild(this.text_input);
        this.select_menu = Y.Node.create(
            '<select id="field.testfield-suggestions"> ' +
            '    <option value="">Did you mean...</option>' +
            '    <option value="fnord">Fnord Snarf (fnord)</option>' +
            '</select>');
        Y.one('body').appendChild(this.select_menu);
        var select_menu = Y.DOM.byId('field.testfield-suggestions');
        var text_input = Y.DOM.byId('field.testfield');
        Y.lp.app.picker.connect_select_menu(select_menu, text_input);
        select_menu.selectedIndex = 1;
        Y.Event.simulate(select_menu, 'change');
        Assert.areEqual(
            'fnord', text_input.value,
            "Select menu's onchange handler failed.");
    }
}));

/*
 * Test cases for assign and remove buttons.
 */
suite.add(new Y.Test.Case({

    name: 'picker_assign_remove_button',

    setUp: function() {
        var i;
        this.vocabulary = new Array(121);
        for (i = 0; i <5; i++) {
            this.vocabulary[i] = {
                "value": "value-" + i,
                "title": "title-" + i,
                "css": "sprite-person",
                "description": "description-" + i,
                "api_uri": "~/fred-" + i};
        }
        this.ME = '/~me';
        window.LP = {
            links: {
                me: this.ME
            },
            cache: {}
        };

        // We patch Launchpad client to return some fake data for the patch
        // operation.
        Y.lp.client.Launchpad = function() {};
        Y.lp.client.Launchpad.prototype.patch =
            function(uri, representation, config, headers) {
                // our setup assumes success, so we just do the success
                // callback.
                var entry_repr = {
                  'lp_html': {'test_link': '<a href="/~me">Content</a>'}
                };
                var result = new Y.lp.client.Entry(
                    null, entry_repr, "a_self_link");
                config.on.success(result);
            };

    },

    tearDown: function() {
        cleanup_widget(this.picker);
        delete window.LP;
    },

    create_picker: function(
        show_assign_me_button, show_remove_button, field_value) {
        if (field_value !== undefined) {
            var data_box = Y.one('#picker_id .yui3-activator-data-box');
            data_box.appendChild(Y.Node.create('<a>Content</a>'));
            data_box.one('a').set('href', field_value);
        }

        var config = {
            "step_title": "Choose someone",
            "header": "Pick Someone",
            "validate_callback": null,
            "show_search_box": true,
            "show_assign_me_button": show_assign_me_button,
            "show_remove_button": show_remove_button,
            "assign_button_text": "Assign Moi",
            "remove_button_text": "Remove someone"
            };
        this.picker = Y.lp.app.picker.addPickerPatcher(
                this.vocabulary,
                "foo/bar",
                "test_link",
                "picker_id",
                config);
    },

    _check_button_state: function(btn_class, is_visible) {
        var assign_me_button = Y.one(btn_class);
        Assert.isNotNull(assign_me_button);
        if (is_visible) {
            Assert.isFalse(
                assign_me_button.hasClass('yui3-picker-hidden'),
                btn_class + " should be visible but is hidden");
        } else {
            Assert.isTrue(
                assign_me_button.hasClass('yui3-picker-hidden'),
                btn_class + " should be hidden but is visible");
        }
    },

    _check_assign_me_button_state: function(is_visible) {
        this._check_button_state('.yui-picker-assign-me-button', is_visible);
    },

    _check_remove_button_state: function(is_visible) {
        this._check_button_state('.yui-picker-remove-button', is_visible);
    },

    test_picker_assign_me_button_text: function() {
        // The assign me button text is correct.
        this.create_picker(true, true);
        this.picker.render();
        var assign_me_button = Y.one('.yui-picker-assign-me-button');
        Assert.areEqual('Assign Moi', assign_me_button.get('innerHTML'))
    },

    test_picker_remove_button_text: function() {
        // The remove button text is correct.
        this.create_picker(true, true);
        this.picker.render();
        var remove_button = Y.one('.yui-picker-remove-button');
        Assert.areEqual('Remove someone', remove_button.get('innerHTML'))
    },

    test_picker_has_assign_me_button: function() {
        // The assign me button is shown.
        this.create_picker(true, true);
        this.picker.render();
        this._check_assign_me_button_state(true);
    },

    test_picker_no_assign_me_button_unless_configured: function() {
        // The assign me button is only rendered if show_assign_me_button
        // config setting is true.
        this.create_picker(false, true);
        this.picker.render();
        Assert.isNull(Y.one('.yui-picker-assign-me-button'));
    },

    test_picker_no_assign_me_button_if_value_is_me: function() {
        // The assign me button is not shown if the picker is created for a
        // field where the value is "me".
        this.create_picker(true, true, this.ME);
        this.picker.render();
        this._check_assign_me_button_state(false);
    },

    test_picker_assign_me_button_hide_on_save: function() {
        // The assign me button is shown initially but hidden if the picker
        // saves a value equal to 'me'.
        this.create_picker(true, true);
        this._check_assign_me_button_state(true);
        this.picker.set('results', this.vocabulary);
        this.picker.render();
        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(1)', 'click');
        this._check_assign_me_button_state(false);
    },

    test_picker_no_remove_button_if_null_value: function() {
        // The remove button is not shown if the picker is created for a field
        // which has a null value.
        this.create_picker(true, true);
        this.picker.render();
        this._check_remove_button_state(false);
    },

    test_picker_has_remove_button_if_value: function() {
        // The remove button is shown if the picker is created for a field
        // which has a value.
        this.create_picker(true, true, this.ME);
        this.picker.render();
        this._check_remove_button_state(true);
    },

    test_picker_no_remove_button_unless_configured: function() {
        // The remove button is only rendered if show_remove_button setting is
        // true.
        this.create_picker(true, false, this.ME);
        this.picker.render();
        Assert.isNull(Y.one('.yui-picker-remove-button'));
    },

    test_picker_remove_button_clicked: function() {
        // The remove button is hidden once a picker value has been removed.
        // And the assign me button is shown.
        this.create_picker(true, true, this.ME);
        this.picker.render();
        var remove = Y.one('.yui-picker-remove-button');
        remove.simulate('click');
        this._check_remove_button_state(false);
        this._check_assign_me_button_state(true);
    },

    test_picker_assign_me_button_clicked: function() {
        // The assign me button is hidden once it is clicked.
        // And the remove button is shown.
        this.create_picker(true, true);
        this.picker.render();
        var remove = Y.one('.yui-picker-assign-me-button');
        remove.simulate('click');
        this._check_remove_button_state(true);
        this._check_assign_me_button_state(false);
    }
}));

/*
 * Test cases for a picker with a large vocabulary.
 */
suite.add(new Y.Test.Case({

    name: 'picker_large_vocabulary',

    setUp: function() {
        var i;
        this.vocabulary = new Array(121);
        for (i = 0; i < 121; i++) {
            this.vocabulary[i] = {
                "value": "value-" + i,
                "title": "title-" + i,
                "css": "sprite-person",
                "description": "description-" + i,
                "api_uri": "~/fred-" + i};
        }
    },

    tearDown: function() {
        cleanup_widget(this.picker);
    },

    create_picker: function(show_search_box) {
        var config = {
            "step_title": "Choose someone",
            "header": "Pick Someone",
            "validate_callback": null
            };
        if (show_search_box !== undefined) {
            config.show_search_box = show_search_box;
        }
        this.picker = Y.lp.app.picker.addPickerPatcher(
                this.vocabulary,
                "foo/bar",
                "test_link",
                "picker_id",
                config);
    },

    test_picker_displays_empty_list: function() {
        // With too many results, the results will be empty.
        this.create_picker(true);
        this.picker.render();
        this.picker.set('min_search_chars', 0);
        this.picker.fire('search', '');
        var result_text = this.picker.get('contentBox')
            .one('.yui3-picker-results').get('text');
        Assert.areEqual('', result_text);
    },

    test_picker_displays_warning: function() {
        // With a search box the picker will refuse to display more than
        // 120 values.
        this.create_picker(true);
        this.picker.set('min_search_chars', 0);
        this.picker.fire('search', '');
        Assert.areEqual(
            'Too many matches. Please try to narrow your search.',
            this.picker.get('error'));
    },

    test_picker_displays_warning_by_default: function() {
        // If show_search_box is not supplied in config, it defaults to true.
        // Thus the picker will refuse to display more than 120 values.
        this.create_picker();
        this.picker.set('min_search_chars', 0);
        this.picker.fire('search', '');
        Assert.areEqual(
            'Too many matches. Please try to narrow your search.',
            this.picker.get('error'));
    },

    test_picker_no_warning: function() {
        // Without a search box the picker will also display more than
        // 120 values.
        this.create_picker(false);
        this.picker.set('min_search_chars', 0);
        this.picker.fire('search', '');
        Assert.areEqual(null, this.picker.get('error'));
    }

}));


// Lock, stock, and two smoking barrels.
var handle_complete = function(data) {
    window.status = '::::' + JSON.stringify(data);
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
