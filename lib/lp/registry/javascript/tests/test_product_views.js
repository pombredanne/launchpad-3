/* Copyright (c) 2012 Canonical Ltd. All rights reserved. */

YUI.add('registry.product-views.test', function (Y) {
    var tests = Y.namespace('registry.product-views.test');

    var ns = Y.namespace('registry.views');
    tests.suite = new Y.Test.Suite('registry.product-views Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'registry.product-views.new_tests',

        setUp: function () {
            window.LP = {
                cache: {
                    context: {
                        web_link: ''
                    },
                    information_type_data: {
                        PUBLIC: {
                            value: 'PUBLIC', name: 'Public',
                            is_private: false, order: 1,
                            description: 'Public Description'
                        },
                        PUBLICSECURITY: {
                            value: 'PUBLICSECURITY', name: 'Public Security',
                            is_private: false, order: 2,
                            description: 'Public Security Description'
                        },
                        PROPRIETARY: {
                            value: 'PROPRIETARY', name: 'Proprietary',
                            is_private: true, order: 3,
                            description: 'Private Description'
                        },
                        USERDATA: {
                            value: 'USERDATA', name: 'Private',
                            is_private: true, order: 4,
                            description: 'Private Description'
                        }
                    }
                }
            };
        },

        tearDown: function () {
            Y.one('#testdom').empty();
            LP.cache = {};
        },

        _setup_url_fields: function () {
            Y.one('#testdom').setContent(
                '<input type="text" id="field.name" name="field.name" />' +
                '<input type="text" id="field.displayname" name="field.displayname" />'
            );
        },

        _setup_information_type: function () {
            var tpl = Y.one('#tpl_information_type');
            var html = Y.lp.mustache.to_html(tpl.getContent());
            Y.one('#testdom').setContent(html);
        },

        test_library_exists: function () {
            Y.Assert.isObject(ns.NewProduct,
                "Could not locate the registry.views.NewProduct module");
        },

        test_url_autofill_sync: function () {
            this._setup_url_fields();
            var view = new ns.NewProduct();
            view.render();

            var name_field = Y.one('input[id="field.displayname"]');
            name_field.set('value', 'test');
            name_field.simulate('keyup');

            Y.Assert.areEqual(
                'test',
                Y.one('input[name="field.name"]').get('value'),
                'The url field should be updated based on the display name');
        },

        test_url_autofill_disables: function () {
            this._setup_url_fields();
            var view = new ns.NewProduct();
            view.render();

            var name_field = Y.one('input[id="field.displayname"]');
            var url_field = Y.one('input[id="field.name"]');
            name_field.set('value', 'test');
            name_field.simulate('keyup');
            Y.Assert.areEqual( 'test', url_field.get('value'),
                'The url field should be updated based on the display name');

            // Now setting the url field manually should detach the event for
            // the sync.
            url_field.set('value', 'test2');
            url_field.simulate('keyup');

            // Changing the value back should fail horribly.
            name_field.set('value', 'test');
            name_field.simulate('keyup');

            Y.Assert.areEqual(
                'test2',
                url_field.get('value'),
                'The url field should not be updated.');
        },

        test_information_type_widget: function () {
            // When we setup the UI with the information type choice we get a
            // choice widget.
            this._setup_information_type();
            var view = new ns.NewProduct();
            view.render();

            Y.Assert.isNotNull(Y.one('#testdom .yui3-ichoicesource'));
        },

        test_information_type_choose_non_public: function () {
            // Selecting an information type not-public hides the license,
            // sets it to commercial, and shows the bug supervisor and driver
            // fields.
            this._setup_information_type();
            var view = new ns.NewProduct();
            view.render();

            var info_type_input = Y.one('input[name="field.information_type"]');
            var called = false;
            view.on('information_type:changed', function (ev) {
                called = true;
                Y.Assert.areEqual('EMBARGOED', ev.input.get('value'),
                                  'input val is set.');
            });

            // We're relying on the tested choiceedit code to change our
            // original radio button control value and we'll listen into that
            // original DOM element vs hooking into the ChoiceEdit widget
            // itself.
            info_type_input.set('value', 'EMBARGOED');
            info_type_input.simulate('change');
            Y.Assert.isTrue(called, 'Changed event was fired.');

            // Now let's make sure the UI is updated.

        }
    }));

}, '0.1', {
    requires: ['test', 'event-simulate', 'node-event-simulate', 'console',
               'lp.mustache', 'registry.product-views']
});
