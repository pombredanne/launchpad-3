YUI.add('lp.bugs.buglisting.test', function (Y) {
    var module = Y.lp.bugs.buglisting;

    var tests = Y.namespace('lp.bugs.buglisting.test');
    tests.suite = new Y.Test.Suite('Buglisting Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'bugs.buglisting_tests',

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.bugs.buglisting,
                "Could not locate the lp.bugs.buglisting module");
        }
    }));

    tests.suite.add(new Y.Test.Case({
        name: 'ListingNavigator',
        setUp: function() {
            this.target = Y.Node.create('<div></div>').set(
                'id', 'client-listing');
            Y.one('body').appendChild(this.target);
        },
        tearDown: function() {
            this.target.remove();
            delete this.target;
            Y.lp.testing.helpers.reset_history();
        },
        test_sets_search_params: function() {
            // search_parms includes all query values that don't control
            // batching
            var navigator = new module.BugListingNavigator({
                current_url: 'http://yahoo.com?foo=bar&start=1&memo=2&' +
                    'direction=3&orderby=4',
                cache: {next: null, prev: null},
                target: this.target
            });
            Y.lp.testing.assert.assert_equal_structure(
                {foo: 'bar'}, navigator.get('search_params'));
        },
        test_cleans_visibility_from_current_batch: function() {
            // When initial batch is handled, field visibility is stripped.
            var navigator = new module.BugListingNavigator({
                current_url: '',
                cache: {
                    field_visibility: {show_item: true},
                    mustache_model: {items: [{show_item: true} ] },
                    next: null,
                    prev: null
                },
                target: this.target
            });
            bugtask = navigator.get_current_batch().mustache_model.items[0];
            Y.Assert.isFalse(bugtask.hasOwnProperty('show_item'));
        },
        test_cleans_visibility_from_new_batch: function() {
            // When new batch is handled, field visibility is stripped.
            var bugtask;
            var model = {
                mustache_model: {items: []},
                memo: 1,
                next: null,
                prev: null,
                field_visibility: {},
                field_visibility_defaults: {show_item: true}
            };
            var navigator = new module.BugListingNavigator({
                current_url: '',
                cache: model,
                template: '',
                target: this.target
            });
            var batch = {
                mustache_model: {
                    items: [{show_item: true}]},
                memo: 2,
                next: null,
                prev: null,
                field_visibility: {show_item: true}
            };
            var query = navigator.get_batch_query(batch);
            navigator.update_from_new_model(query, false, batch);
            bugtask = navigator.get_current_batch().mustache_model.items[0];
            Y.Assert.isFalse(bugtask.hasOwnProperty('show_item'));
        }
    }));

    tests.suite.add(new Y.Test.Case({
        name: 'from_page tests',
        setUp: function() {
            window.LP = {
                cache: {
                    current_batch: {},
                    next: null,
                    prev: null,
                    related_features: {
                        'bugs.dynamic_bug_listings.pre_fetch': {value: 'on'}
                    }
                }
            };
        },
        getPreviousLink: function() {
            return Y.one('.previous').get('href');
        },
        test_from_page_with_client: function() {
            Y.one('#fixture').setContent(
                '<a class="previous" href="http://example.org/">PreVious</span>' +
                '<div id="client-listing"></div>');
            Y.Assert.areSame('http://example.org/', this.getPreviousLink());
            module.BugListingNavigator.from_page();
            Y.Assert.areNotSame('http://example.org/', this.getPreviousLink());
        },
        test_from_page_with_no_client: function() {
            Y.one('#fixture').setContent('');
            var navigator = module.BugListingNavigator.from_page();
            Y.Assert.isNull(navigator);
        },
        tearDown: function() {
            Y.one('#fixture').setContent("");
            delete window.LP;
        }
    }));


}, '0.1', {
    'requires': ['test', 'lp.testing.helpers', 'console',
        'lp.bugs.buglisting', 'lp.testing.mockio', 'lp.testing.assert',
        'lp.app.inlinehelp']
});
