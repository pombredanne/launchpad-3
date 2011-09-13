/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'node', 'lp', 'lp.client',
        'event-focus', 'event-simulate', 'lazr.picker', 'lazr.person-picker',
        'lp.app.picker', 'node-event-simulate', 'escape', 'event',
        'lp.testing.mockio',
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
                "description": "fred@example.com", "api_uri": "~/fred",
                "metadata": "person"},
            {"value": "frieda", "title": "Frieda", "css": "sprite-team",
                "description": "frieda@example.com", "api_uri": "~/frieda",
                "metadata": "team"}
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

    create_picker: function(validate_callback, extra_config) {
        var config = {
                "step_title": "Choose someone",
                "header": "Pick Someone",
                "null_display_value": "Noone",
                "validate_callback": validate_callback
        };
        if (extra_config !== undefined) {
           config = Y.merge(extra_config, config);
        }
        this.picker = Y.lp.app.picker.addPickerPatcher(
            this.vocabulary,
            "foo/bar",
            "test_link",
            "picker_id",
            config);
    },

    create_picker_direct: function(associated_field) {
        this.picker = Y.lp.app.picker.create(
            this.vocabulary,
            undefined,
            associated_field);
    },

    test_picker_can_be_instantiated: function() {
        // The picker can be instantiated.
        this.create_picker();
        Assert.isInstanceOf(
            Y.lazr.picker.Picker, this.picker,
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
        this.create_picker_direct('field.testfield');
        this.picker.set('results', this.vocabulary);
        this.picker.render();
        var got_focus = false;
        this.text_input.on('focus', function(e) {
            got_focus = true;
        });
        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(2)', 'click');
        Assert.areEqual(
            'frieda', Y.one('[id="field.testfield"]').get("value"));
        Assert.areEqual('team', this.picker.get('selected_value_metadata'));
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

    test_extra_no_results_message: function () {
        this.create_picker(
            undefined, {'extra_no_results_message': 'message'});
        this.picker.set('results', []);
        var footer_slot = this.picker.get('footer_slot');
        Assert.areEqual('message', footer_slot.get('text'));
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

    create_picker: function(show_search_box, extra_config) {
        var config = {
            "step_title": "Choose someone",
            "header": "Pick Someone",
            "validate_callback": null
            };
        if (show_search_box !== undefined) {
            config.show_search_box = show_search_box;
        }
        if (extra_config !== undefined) {
           config = Y.merge(extra_config, config);
        }
        this.picker = Y.lp.app.picker.addPickerPatcher(
                this.vocabulary,
                "foo/bar",
                "test_link",
                "picker_id",
                config);
    },

    test_filter_options_initialisation: function() {
        // Filter options are correctly used to set up the picker.
        this.picker = Y.lp.app.picker.create(
            this.vocabulary, undefined, undefined, ['a', 'b', 'c']);
        Y.ArrayAssert.itemsAreEqual(
            ['a', 'b', 'c'], this.picker.get('filter_options'));
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
    },

    test_vocab_filter_config: function () {
        // The vocab filter config is correctly used to create the picker.
        var filters = [{name: 'ALL', title: 'All', description: 'All'}];
        this.create_picker(undefined,  {'vocabulary_filters': filters});
        var filter_options = this.picker.get('filter_options');
        Assert.areEqual(filters, filter_options);
    }
}));

suite.add(new Y.Test.Case({

    name: 'picker_error_handling',

    setUp: function() {
        this.create_picker();
        this.picker.fire('search', 'foo');
    },

    tearDown: function() {
        cleanup_widget(this.picker);
    },

    create_picker: function() {
        this.mock_io = new Y.lp.testing.mockio.MockIo();
        this.picker = Y.lp.app.picker.addPickerPatcher(
            "Foo",
            "foo/bar",
            "test_link",
            "picker_id",
            {yio: this.mock_io});
    },

    get_oops_headers: function(oops) {
        var headers = {};
        headers['X-Lazr-OopsId'] = oops;
        return headers;
    },

    test_oops: function() {
        // A 500 (ISE) with an OOPS ID informs the user that we've
        // logged it, and gives them the OOPS ID.
        this.mock_io.failure(
            {responseHeaders: this.get_oops_headers('OOPS')});
        Assert.areEqual(
            "Sorry, something went wrong with your search. We've recorded " +
            "what happened, and we'll fix it as soon as possible. " +
            "(Error ID: OOPS)",
            this.picker.get('error'));
    },

    test_timeout: function() {
        // A 503 (timeout) or 502/504 (proxy error) informs the user
        // that they should retry, and gives them the OOPS ID.
        this.mock_io.failure(
            {status: 503, responseHeaders: this.get_oops_headers('OOPS')});
        Assert.areEqual(
            "Sorry, something went wrong with your search. Trying again " +
            "in a couple of minutes might work. (Error ID: OOPS)",
            this.picker.get('error'));
    },

    test_other_error: function() {
        // Any other type of error just displays a generic failure
        // message, with no OOPS ID.
        this.mock_io.failure({status: 400});
        Assert.areEqual(
            "Sorry, something went wrong with your search.",
            this.picker.get('error'));
    }
}));

suite.add(new Y.Test.Case({

    name: 'picker_automated_search',

    create_picker: function(yio) {
        var config = {yio: yio};
        return Y.lp.app.picker.addPickerPatcher(
            "Foo",
            "foo/bar",
            "test_link",
            "picker_id",
            config);
    },

    make_response: function(status, oops, responseText) {
        if (oops === undefined) {
            oops = null;
        }
        return {
            status: status,
            responseText: responseText,
            getResponseHeader: function(header) {
                if (header === 'X-Lazr-OopsId') {
                    return oops;
                }
            }
        };
    },

    test_automated_search_results_ignored_if_user_has_searched: function() {
        // If an automated search (like loading branch suggestions) returns
        // results and the user has submitted a search, then the results of
        // the automated search are ignored so as not to confuse the user.
        var mock_io = new Y.lp.testing.mockio.MockIo();
        var picker = this.create_picker(mock_io);
        // First an automated search is run.
        picker.fire('search', 'guess', undefined, true);
        // Then the user initiates their own search.
        picker.fire('search', 'test');
        // Two requests have been sent out.
        Y.Assert.areEqual(2, mock_io.requests.length);
        // Respond to the automated request.
        mock_io.requests[0].respond({responseText: '{"entries": 1}'});
        // ... the results are ignored.
        Assert.areNotEqual(1, picker.get('results'));
        // Respond to the user request.
        mock_io.requests[1].respond({responseText: '{"entries": 2}'});
        Assert.areEqual(2, picker.get('results'));
        cleanup_widget(picker);
    },

    test_automated_search_error_ignored_if_user_has_searched: function() {
        // If an automated search (like loading branch suggestions) returns an
        // error and the user has submitted a search, then the error from the
        // automated search is ignored so as not to confuse the user.
        var mock_io = new Y.lp.testing.mockio.MockIo();
        var picker = this.create_picker(mock_io);
        picker.fire('search', 'test');
        picker.fire('search', 'guess', undefined, true);
        mock_io.failure();
        Assert.areEqual(null, picker.get('error'));
        cleanup_widget(picker);
    }

}));

Y.lp.testing.Runner.run(suite);

});
