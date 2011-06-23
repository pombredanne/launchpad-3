/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: false
    }).use('test', 'console', 'plugin', 'lp.app.widgets',
           'node-event-simulate', function(Y) {

    var suite = new Y.Test.Suite("lp.app.widgets.PersonPicker Tests");

    suite.add(new Y.Test.Case({
        name: 'personpicker',

        setUp: function() {
            window.LP = {
                links: {me: '/~no-one'},
                cache: {}
            };
            this.vocabulary = [
                {
                    "value": "fred",
                    "title": "Fred",
                    "css": "sprite-person",
                    "description": "fred@example.com",
                    "api_uri": "~/fred"
                },
                {
                    "value": "frieda",
                    "title": "Frieda",
                    "css": "sprite-person",
                    "description": "frieda@example.com",
                    "api_uri": "~/frieda"
                }
            ];
        },

        test_render: function () {
            var personpicker = new Y.lp.app.widgets.PersonPicker();
            personpicker.render();
            personpicker.show();

            // The extra buttons section exists
            Y.Assert.isNotNull(Y.one('.extra-form-buttons'));
            Y.Assert.isNotUndefined(personpicker.assign_me_button);
            Y.Assert.isNotUndefined(personpicker.remove_button);
        },

        test_search_field_focus: function () {
            var personpicker = new Y.lp.app.widgets.PersonPicker();
            personpicker.render();
            personpicker.hide();

            var got_focus = false;
            personpicker._search_input.on('focus', function(e) {
                got_focus = true;
            });
            personpicker.show();
            Y.Assert.isTrue(got_focus, "search input did not get focus.");
        },

        test_buttons: function () {
            var personpicker = new Y.lp.app.widgets.PersonPicker();
            personpicker.render();
            personpicker.show();

            // Patch the picker so the assign_me and remove methods can be
            // tested.
            var data = null;
            personpicker.on('save', function (result) {
                data = result.value;
            });
            var remove = Y.one('.yui-picker-remove-button');
            remove.simulate('click');
            Y.Assert.areEqual('', data);

            var assign_me = Y.one('.yui-picker-assign-me-button');
            assign_me.simulate('click');
            Y.Assert.areEqual('no-one', data);
        },

        test_buttons_config: function () {
            cfg = {
                show_assign_me_button: false,
                show_remove_button: false
            };

            personpicker = new Y.lp.app.widgets.PersonPicker(cfg);
            personpicker.render();
            personpicker.show();

            Y.Assert.isNotNull(Y.one('.extra-form-buttons'));
            Y.Assert.isUndefined(personpicker.remove_button);
            Y.Assert.isUndefined(personpicker.assign_me_button);
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
            personpicker = new Y.lp.app.widgets.PersonPicker(cfg);
            personpicker.render();
            this._change_results(personpicker, false);
            Y.Assert.isTrue(personpicker._extra_buttons.hasClass('unseen'));

            this._change_results(personpicker, true);
            Y.Assert.isFalse(personpicker._extra_buttons.hasClass('unseen'));
        }
    }));

    // Lock, stock, and two smoking barrels.
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

