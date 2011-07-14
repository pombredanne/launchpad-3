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
 * Test cases for assign and remove buttons.
 */
suite.add(new Y.Test.Case({

    name: 'picker_assign_remove_button',

    setUp: function() {
        this.ME = '/~me';
        window.LP = {
                links: {me: this.ME},
            cache: {}
        };
        this.vocabulary = [
            {
                "value": "me",
                "title": "Me",
                "css": "sprite-person",
                "description": "me@example.com",
                "api_uri": "~/me"
            },
            {
                "value": "someone",
                "title": "Someone Else",
                "css": "sprite-person",
                "description": "someone@example.com",
                "api_uri": "~/someone"
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
        if (show_assign_me_button === undefined) {
            show_assign_me_button = false;
        }
        if (show_remove_button === undefined) {
            show_remove_button = false;
        }

        var config = {
            "step_title": "Choose someone",
            "header": "Pick Someone",
            "validate_callback": null,
            "show_search_box": true,
            "show_assign_me_button": show_assign_me_button,
            "show_remove_button": show_remove_button,
            "assign_button_text": "Assign Moi",
            "remove_button_text": "Remove someone",
            "picker_type": 'person'
            };
        this.picker = Y.lp.app.picker.addPickerPatcher(
                this.vocabulary,
                "foo/bar",
                "test_link",
                "picker_id",
                config);
    },

    test_search_field_focus: function () {
        // The search field has focus when the picker is shown.
        this.create_picker();
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
        this.picker = new Y.lazr.picker.PersonPicker();
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
        Y.Assert.areEqual('', data);

        var assign_me = Y.one('.yui-picker-assign-me-button');
        assign_me.simulate('click');
        Y.Assert.areEqual('me', data);
    },

    _change_results: function (picker, no_result) {
        // simulates search by setting a value and the result
        picker._search_input.set('value', 'foo');
        if (no_result) {
            picker.set('results', []);
        } else {
            picker.set('results', this.vocabulary);
        }
    },

    test_buttons_vanish: function () {
        // The assign/remove links are hidden when a search is performed.
        this.create_picker(true, true);
        this.picker.render();
        this._change_results(this.picker, false);
        Y.Assert.isTrue(this.picker._extra_buttons.hasClass('unseen'));

        this._change_results(this.picker, true);
        Y.Assert.isFalse(this.picker._extra_buttons.hasClass('unseen'));
    },

    test_buttons_reappear: function () {
        // The assign/remove links are shown again after doing a search and
        // selecting a result. Doing a search hides the links so we need to
        // ensure they are made visible again.
        this.create_picker(true, true);
        this.picker.render();
        this._change_results(this.picker, false);
        Y.Assert.isTrue(this.picker._extra_buttons.hasClass('unseen'));
        simulate(
            this.picker.get('boundingBox'), '.yui3-picker-results li', 'click');
        Y.Assert.isFalse(this.picker._extra_buttons.hasClass('unseen'));
    }
}));

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
