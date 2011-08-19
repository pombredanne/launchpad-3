/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI().use('test', 'console', 'plugin',
           'lazr.picker', 'lazr.person-picker', 'lp.app.picker',
           'node-event-simulate', function(Y) {

var Assert = Y.Assert;

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

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var rawnode = Y.Node.getDOMNode(widget.one(selector));
    Y.Event.simulate(rawnode, evtype, options);
}

var suite = new Y.Test.Suite("PersonPicker Tests");

/*
 * Test cases for person picker functionality.
 */
var commonPersonPickerTests = {

    name: 'common_person_picker',

    setUp: function() {
        this.ME = '/~me';
        window.LP = {
                links: {me: this.ME},
            cache: {}
        };
        this.vocabulary = [
            {
                "value": "me",
                "metadata": "person",
                "title": "Me",
                "css": "sprite-person",
                "description": "me@example.com",
                "api_uri": "/~me"
            },
            {
                "value": "someteam",
                "metadata": "team",
                "title": "Some Team",
                "css": "sprite-team",
                "description": "someone@example.com",
                "api_uri": "/~someteam"
            }
        ];

        // We patch Launchpad client to return some fake data for the patch
        // operation.
        Y.lp.client.Launchpad = function() {};
        Y.lp.client.Launchpad.prototype.patch =
            function(uri, representation, config, headers) {
                // our setup assumes success, so we just do the success
                // callback.
                var entry_repr = {
                  'test_link': representation.test_link,
                  'lp_html': {
                      'test_link':
                          '<a href="' + representation.test_link +
                              '">Content</a>'}
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

    _picker_params: function(
        show_assign_me_button, show_remove_button,
        selected_value, selected_value_metadata) {
        return {
            "show_assign_me_button": show_assign_me_button,
            "show_remove_button": show_remove_button,
            "selected_value": selected_value,
            "selected_value_metadata": selected_value_metadata
        };
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

    test_search_field_focus: function () {
        // The search field has focus when the picker is shown.
        this.create_picker(this._picker_params(true, true));
        this.picker.render();
        this.picker.hide();

        var got_focus = false;
        this.picker._search_input.on('focus', function(e) {
            got_focus = true;
        });
        this.picker.show();
        Y.Assert.isTrue(got_focus, "search input did not get focus.");
    },

    test_buttons_save: function () {
        // The assign/remove links save the correct values.
        this.create_picker(this._picker_params(true, true));
        this.picker.render();
        this.picker.show();

        // Patch the picker so the assign_me and remove methods can be
        // tested.
        var data = null;
        this.picker.on('save', function (result) {
            data = result.value;
        });
        var remove = Y.one('.yui-picker-remove-button');
        remove.simulate('click');
        Y.Assert.areEqual(null, data);

        var assign_me = Y.one('.yui-picker-assign-me-button');
        assign_me.simulate('click');
        Y.Assert.areEqual('me', data);
    },

    test_picker_assign_me_button_text: function() {
        // The assign me button text is correct.
        this.create_picker(this._picker_params(true, true));
        this.picker.render();
        var assign_me_button = Y.one('.yui-picker-assign-me-button');
        Assert.areEqual('Assign Moi', assign_me_button.get('innerHTML'));
    },

    test_picker_assign_me_button_not_shown_when_not_logged_in: function() {
        // The assign me button is hidden when the user is not logged-in.
        delete window.LP.links.me;  // Log-out.
        this.create_picker(this._picker_params(true, true));
        this.picker.render();
        var assign_me_button = Y.one('.yui-picker-assign-me-button');
        Assert.isNull(assign_me_button);
    },

    test_picker_remove_person_button_text: function() {
        // The remove button text is correct.
        this.create_picker(this._picker_params(true, true, "fred", "person"));
        this.picker.render();
        var remove_button = Y.one('.yui-picker-remove-button');
        Assert.areEqual('Remove someone', remove_button.get('innerHTML'));
    },

    test_picker_remove_team_button_text: function() {
        // The remove button text is correct.
        this.create_picker(this._picker_params(true, true, "cats", "team"));
        this.picker.render();
        var remove_button = Y.one('.yui-picker-remove-button');
        Assert.areEqual('Remove some team', remove_button.get('innerHTML'));
    },

    test_picker_has_assign_me_button: function() {
        // The assign me button is shown.
        this.create_picker(this._picker_params(true, true));
        this.picker.render();
        this._check_assign_me_button_state(true);
    },

    test_picker_no_assign_me_button_unless_configured: function() {
        // The assign me button is only rendered if show_assign_me_button
        // config setting is true.
        this.create_picker(this._picker_params(false, true));
        this.picker.render();
        Assert.isNull(Y.one('.yui-picker-assign-me-button'));
    },

    test_picker_no_assign_me_button_if_value_is_me: function() {
        // The assign me button is not shown if the picker is created for a
        // field where the value is "me".
        this.create_picker(this._picker_params(true, true, "me"), this.ME);
        this.picker.render();
        this._check_assign_me_button_state(false);
    },

    test_picker_no_remove_button_if_null_value: function() {
        // The remove button is not shown if the picker is created for a field
        // which has a null value.
        this.create_picker(this._picker_params(true, true));
        this.picker.render();
        this._check_remove_button_state(false);
    },

    test_picker_has_remove_button_if_value: function() {
        // The remove button is shown if the picker is created for a field
        // which has a value.
        this.create_picker(this._picker_params(true, true, "me"), this.ME);
        this.picker.render();
        this._check_remove_button_state(true);
    },

    test_picker_no_remove_button_unless_configured: function() {
        // The remove button is only rendered if show_remove_button setting is
        // true.
        this.create_picker(this._picker_params(true, false, "me"), this.ME);
        this.picker.render();
        Assert.isNull(Y.one('.yui-picker-remove-button'));
    }
};

/*
 * Test cases for person picker functionality when created using
 * addPickerPatcher.
 */
var pickerPatcherPersonPickerTests = {

    name: 'picker_patcher_person_picker',

    create_picker: function(params, field_value) {
        if (field_value !== undefined) {
            var data_box = Y.one('#picker_id .yui3-activator-data-box');
            data_box.appendChild(Y.Node.create('<a>Content</a>'));
            data_box.one('a').set('href', field_value);
        }

        var config = {
            "picker_type": "person",
            "step_title": "Choose someone",
            "header": "Pick Someone",
            "validate_callback": null,
            "show_search_box": true,
            "show_assign_me_button": params.show_assign_me_button,
            "show_remove_button": params.show_remove_button,
            "selected_value": params.selected_value,
            "selected_value_metadata": params.selected_value_metadata,
            "assign_me_text": "Assign Moi",
            "remove_person_text": "Remove someone",
            "remove_team_text": "Remove some team"
            };
        this.picker = Y.lp.app.picker.addPickerPatcher(
                this.vocabulary,
                "foo/bar",
                "test_link",
                "picker_id",
                config);
    },

    test_picker_assign_me_button_hide_on_save: function() {
        // The assign me button is shown initially but hidden if the picker
        // saves a value equal to 'me'.
        this.create_picker(this._picker_params(true, true));
        this._check_assign_me_button_state(true);
        this.picker.set('results', this.vocabulary);
        this.picker.render();
        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(1)', 'click');
        this._check_assign_me_button_state(false);
    },

    test_picker_remove_button_clicked: function() {
        // The remove button is hidden once a picker value has been removed.
        // And the assign me button is shown.
        this.create_picker(this._picker_params(true, true, "me"), this.ME);
        this.picker.render();
        this._check_assign_me_button_state(false);
        var remove = Y.one('.yui-picker-remove-button');
        remove.simulate('click');
        this._check_remove_button_state(false);
        this._check_assign_me_button_state(true);
    },

    test_picker_assign_me_button_clicked: function() {
        // The assign me button is hidden once it is clicked.
        // And the remove button is shown.
        this.create_picker(this._picker_params(true, true));
        this.picker.render();
        var assign_me = Y.one('.yui-picker-assign-me-button');
        assign_me.simulate('click');
        this._check_remove_button_state(true);
        this._check_assign_me_button_state(false);
    },

    test_picker_assign_me_updates_remove_text: function() {
        // When Assign me is used, the Remove button text is updated from
        // the team removal text to the person removal text.
        this.create_picker(this._picker_params(true, true, "cats", "team"));
        this.picker.render();
        var remove_button = Y.one('.yui-picker-remove-button');
        Assert.areEqual('Remove some team', remove_button.get('innerHTML'));
        var assign_me = Y.one('.yui-picker-assign-me-button');
        assign_me.simulate('click');
        Assert.areEqual('Remove someone', remove_button.get('innerHTML'));
    },

    test_picker_save_updates_remove_text: function() {
        // When save is called, the Remove button text is updated according to
        // the newly saved value.
        this.create_picker(this._picker_params(true, true, "me"), this.ME);
        var remove_button = Y.one('.yui-picker-remove-button');
        Assert.areEqual('Remove someone', remove_button.get('innerHTML'));
        this.picker.set('results', this.vocabulary);
        this.picker.render();
        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(2)', 'click');
        Assert.areEqual('Remove some team', remove_button.get('innerHTML'));
    }
};

/*
 * Test cases for person picker functionality when created using
 * addPickerPatcher.
 */
var createDirectPersonPickerTests = {

    name: 'create_direct_person_picker',

    tearDown: function() {
        cleanup_widget(this.picker);
        this.search_input.remove();
        delete window.LP;
    },

    create_picker: function(params, field_value) {
        var associated_field_id;
        this.search_input = Y.Node.create(
                '<input id="field_initval" value="foo"/>');
        Y.one(document.body).appendChild(this.search_input);
        associated_field_id = 'field_initval';
        var text_field = Y.one('#field_initval');
        if (field_value !== undefined) {
            text_field.set('text', field_value);
        }
        var config = {
            "picker_type": "person",
            "associated_field_id": associated_field_id,
            "show_assign_me_button": params.show_assign_me_button,
            "show_remove_button": params.show_remove_button,
            "selected_value": params.selected_value,
            "selected_value_metadata": params.selected_value_metadata,
            "assign_me_text": "Assign Moi",
            "remove_person_text": "Remove someone",
            "remove_team_text": "Remove some team"
            };
        this.picker = Y.lp.app.picker.create(
                            this.vocabulary, config, associated_field_id);
    },

    test_picker_assign_me_button_hide_on_save: function() {
        // The assign me button is shown initially but hidden if the picker
        // saves a value equal to 'me'.
        this.create_picker(this._picker_params(true, true));
        this._check_assign_me_button_state(true);
        this.picker.set('results', this.vocabulary);
        this.picker.render();
        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(1)', 'click');
        this._check_assign_me_button_state(false);
    },

    test_picker_remove_button_clicked: function() {
        // The remove button is hidden once a picker value has been removed.
        // And the assign me button is shown.
        this.create_picker(this._picker_params(true, true, "me"), this.ME);
        this.picker.render();
        this._check_assign_me_button_state(false);
        var remove = Y.one('.yui-picker-remove-button');
        remove.simulate('click');
        this._check_remove_button_state(false);
        this._check_assign_me_button_state(true);
    },

    test_picker_assign_me_button_clicked: function() {
        // The assign me button is hidden once it is clicked.
        // And the remove button is shown.
        this.create_picker(this._picker_params(true, true));
        this.picker.render();
        var assign_me = Y.one('.yui-picker-assign-me-button');
        assign_me.simulate('click');
        this._check_remove_button_state(true);
        this._check_assign_me_button_state(false);
    },

    test_picker_assign_me_updates_remove_text: function() {
        // When Assign me is used, the Remove button text is updated from
        // the team removal text to the person removal text.
        this.create_picker(this._picker_params(true, true, "cats", "team"));
        this.picker.render();
        var remove_button = Y.one('.yui-picker-remove-button');
        Assert.areEqual('Remove some team', remove_button.get('innerHTML'));
        var assign_me = Y.one('.yui-picker-assign-me-button');
        assign_me.simulate('click');
        Assert.areEqual('Remove someone', remove_button.get('innerHTML'));
    },

    test_picker_save_updates_remove_text: function() {
        // When save is called, the Remove button text is updated according to
        // the newly saved value.
        this.create_picker(this._picker_params(true, true, "me"), this.ME);
        var remove_button = Y.one('.yui-picker-remove-button');
        Assert.areEqual('Remove someone', remove_button.get('innerHTML'));
        this.picker.set('results', this.vocabulary);
        this.picker.render();
        simulate(
            this.picker.get('boundingBox').one('.yui3-picker-results'),
                'li:nth-child(2)', 'click');
        Assert.areEqual('Remove some team', remove_button.get('innerHTML'));
    }
};

suite.add(new Y.Test.Case(
  Y.merge(
      commonPersonPickerTests,
      pickerPatcherPersonPickerTests)
));

suite.add(new Y.Test.Case(
  Y.merge(
      commonPersonPickerTests,
      createDirectPersonPickerTests)
));

// Hook for the test runner to get test results.
var handle_complete = function(data) {
    window.status = '::::' + JSON.stringify(data);
};
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
