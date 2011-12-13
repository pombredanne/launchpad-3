YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.buglisting', 'lp.testing.mockio',
           'lp.testing.assert',
           function(Y) {

var suite = new Y.Test.Suite("lp.bugs.buglisting Tests");
var module = Y.lp.bugs.buglisting;


suite.add(new Y.Test.Case({
    name: 'ListingNavigator',
    setUp: function() {
        this.target = Y.Node.create('<div></div>').set(
            'id', 'client-listing');
        Y.one('body').appendChild(this.target);
    },
    tearDown: function() {
        this.target.remove();
        delete this.target;
    },
    test_sets_search_params: function() {
        // search_parms includes all query values that don't control batching
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
                mustache_model: {bugtasks: [{show_item: true} ] },
                next: null,
                prev: null
            },
            target: this.target
        });
        bugtask = navigator.get_current_batch().mustache_model.bugtasks[0];
        Y.Assert.isFalse(bugtask.hasOwnProperty('show_item'));
    },
    test_cleans_visibility_from_new_batch: function() {
        // When new batch is handled, field visibility is stripped.
        var bugtask;
        var model = {
            mustache_model: {bugtasks: []},
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
                bugtasks: [{show_item: true}]},
            memo: 2,
            next: null,
            prev: null,
            field_visibility: {show_item: true}
        };
        var query = navigator.get_batch_query(batch);
        navigator.update_from_new_model(query, false, batch);
        bugtask = navigator.get_current_batch().mustache_model.bugtasks[0];
        Y.Assert.isFalse(bugtask.hasOwnProperty('show_item'));
    }
}));


var get_navigator = function(url, config) {
    var mock_io = new Y.lp.testing.mockio.MockIo();
    if (Y.Lang.isUndefined(url)){
        url = '';
    }
    if (Y.Lang.isUndefined(config)){
        config = {};
    }
    var target = config.target;
    if (!Y.Lang.isValue(target)){
        var target_parent = Y.Node.create('<div></div>');
        target = Y.Node.create('<div "id=#client-listing"></div>');
        target_parent.appendChild(target);
    }
    lp_cache = {
        context: {
            resource_type_link: 'http://foo_type',
            web_link: 'http://foo/bar'
        },
        view_name: '+bugs',
        next: {
            memo: 467,
            start: 500
        },
        prev: {
            memo: 457,
            start: 400
        },
        forwards: true,
        order_by: 'foo',
        memo: 457,
        start: 450,
        last_start: 23,
        field_visibility: {},
        field_visibility_defaults: {}
    };
    if (config.no_next){
        lp_cache.next = null;
    }
    if (config.no_prev){
        lp_cache.prev = null;
    }
    var navigator_config = {
        current_url: url,
        cache: lp_cache,
        io_provider: mock_io,
        pre_fetch: config.pre_fetch,
        target: target,
        template: ''
    };
    return new module.BugListingNavigator(navigator_config);
};

suite.add(new Y.Test.Case({
    name: 'browser history',

    setUp: function() {
        this.target = Y.Node.create('<div></div>').set(
            'id', 'client-listing');
        Y.one('body').appendChild(this.target);
    },

    tearDown: function() {
        this.target.remove();
        delete this.target;
    },

    /**
     * Update from cache generates a change event for the specified batch.
     */
    test_update_from_cache_generates_event: function(){
        var navigator = get_navigator('', {target: this.target});
        var e = null;
        navigator.get('model').get('history').on('change', function(inner_e){
            e = inner_e;
        });
        navigator.get('batches')['some-batch-key'] = {
            mustache_model: {
                bugtasks: []
            },
            next: null,
            prev: null
        };
        navigator.update_from_cache({foo: 'bar'}, 'some-batch-key');
        Y.Assert.areEqual('some-batch-key', e.newVal.batch_key);
        Y.Assert.areEqual('?foo=bar', e._options.url);
    },

    /**
     * When a change event is emitted, the relevant batch becomes the current
     * batch and is rendered.
     */
    test_change_event_renders_cache: function(){
        var navigator = get_navigator('', {target: this.target});
        var batch = {
            mustache_model: {
                bugtasks: [],
                foo: 'bar'
            },
            next: null,
            prev: null
        };
        navigator.set('template', '{{foo}}');
        navigator.get('batches')['some-batch-key'] = batch;
        navigator.get('model').get('history').addValue(
            'batch_key', 'some-batch-key');
        Y.Assert.areEqual(batch, navigator.get_current_batch());
        Y.Assert.areEqual('bar', navigator.get('target').getContent());
    }
}));

suite.add(new Y.Test.Case({
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
