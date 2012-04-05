/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.registry.sharing.shareelisting_navigator.test',
    function (Y) {

    var tests = Y.namespace(
        'lp.registry.sharing.shareelisting_navigator.test');
    tests.suite = new Y.Test.Suite(
        'lp.registry.sharing.shareelisting_navigator Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.registry.sharing.shareelisting_navigator',

        setUp: function () {
            this.fixture = Y.one('#fixture');
            var sharee_table = Y.Node.create(
                    Y.one('#sharee-table-template').getContent());
            this.fixture.appendChild(sharee_table);

        },

        tearDown: function () {
            if (this.fixture !== null) {
                this.fixture.empty();
            }
            delete this.fixture;
        },

        _create_Widget: function() {
            var ns = Y.lp.registry.sharing.shareelisting_navigator;
            return new ns.ShareeListingNavigator({
                cache: {},
                target: Y.one('#sharee-table')
            });
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.sharing.shareelisting_navigator,
                "Could not locate the " +
                "lp.registry.sharing.shareelisting_navigator module");
        },

        test_widget_can_be_instantiated: function() {
            this.navigator = this._create_Widget();
            var ns = Y.lp.registry.sharing.shareelisting_navigator;
            Y.Assert.isInstanceOf(
                ns.ShareeListingNavigator,
                this.navigator,
                "Sharee listing navigator failed to be instantiated");
        }
    }));

}, '0.1', {'requires': ['test', 'console',
        'lp.registry.sharing.shareelisting_navigator'
    ]});
