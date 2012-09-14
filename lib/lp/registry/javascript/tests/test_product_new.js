/* Copyright (c) 2012 Canonical Ltd. All rights reserved. */

YUI.add('lp.registry.product.new.test', function (Y) {

    var tests = Y.namespace('lp.registry.product.new.test');
    tests.suite = new Y.Test.Suite('registry.product.new Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'registry.product.new_tests',

        setUp: function () {},
        tearDown: function () {
            Y.one('#testdom').empty();
        },

        _setup_url_fields: function () {
            Y.one('#testdom').setContent(
                '<input type="text" id="field.name" name="field.name" />' +
                '<input type="text" id="field.displayname" name="field.displayname" />'
            );
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.product.new,
                "Could not locate the lp.registry.product.new module");
        },

        test_url_autofill_sync: function () {
            this._setup_url_fields();
            var view = new Y.lp.registry.product.new.View();
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
            var view = new Y.lp.registry.product.new.View();
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
        }
    }));

}, '0.1', {
    requires: ['test', 'event-simulate', 'console',
               'lp.registry.product.new']
});
