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
    test_sets_search_params: function(){
        // search_parms includes all query values that don't control batching
        var navigator = new module.ListingNavigator(
            'http://yahoo.com?foo=bar&start=1&memo=2&direction=3&orderby=4');
        Y.lp.testing.assert.assert_equal_structure(
            {foo: 'bar'}, navigator.search_params);
    }
}));

suite.add(new Y.Test.Case({
    name: 'rendertable',

    test_rendertable_no_client_listing: function() {
        // Rendering should not error with no #client-listing.
        var navigator = new module.ListingNavigator();
        navigator.rendertable();
    },
    test_rendertable: function() {
        // Rendering should work with #client-listing supplied.
        var target = Y.Node.create('<div id="client-listing"></div>');
        var lp_cache = {
            mustache_model: {
                foo: 'bar'
            }
        };
        var template = "{{foo}}";
        var navigator = new module.ListingNavigator(
            null, lp_cache, template, target);
        navigator.rendertable();
        Y.Assert.areEqual('bar', navigator.target.get('innerHTML'));
    }
}));

suite.add(new Y.Test.Case({
    name: 'change_ordering',

    get_intensity_listing: function(){
        mock_io = new Y.lp.testing.mockio.MockIo();
        lp_cache = {
            context: {
                resource_type_link: 'http://foo_type',
                web_link: 'http://foo/bar'
            },
            mustache_model: {
                foo: 'bar'
            }
        };
        var target = Y.Node.create('<div id="client-listing"></div>');
        var navigator = new module.ListingNavigator(
            "http://yahoo.com?start=5&memo=6&direction=backwards",
            lp_cache, "<ol>" + "{{#item}}<li>{{name}}</li>{{/item}}</ol>",
            target, mock_io);
        navigator.change_ordering('intensity');
        Y.Assert.areEqual('', navigator.target.get('innerHTML'));
        mock_io.last_request.successJSON({
            context: {
                resource_type_link: 'http://foo_type',
                web_link: 'http://foo/bar'
            },
            mustache_model:
            {item: [
                {name: 'first'},
                {name: 'second'}
            ]},
            order_by: 'intensity',
            start: 0,
            forwards: true,
            memo: null
        });
        return navigator;
    },
    test_change_ordering: function() {
        /* change_ordering retrieves a listing for the new ordering and
         * displays it */
        var navigator = this.get_intensity_listing();
        var mock_io = navigator.io_provider;
        Y.Assert.areEqual('<ol><li>first</li><li>second</li></ol>',
            navigator.target.get('innerHTML'));
        Y.Assert.areEqual('/bar/+bugs/++model++?orderby=intensity&start=0',
            mock_io.last_request.url);
    },
    test_change_ordering_uses_cache: function() {
        /* change_ordering will use the cached value instead of making a
         * second AJAX request. */
        var navigator = this.get_intensity_listing();
        Y.Assert.areEqual(1, navigator.io_provider.requests.length);
        navigator.change_ordering('intensity');
        Y.Assert.areEqual(1, navigator.io_provider.requests.length);
    }
}));

suite.add(new Y.Test.Case({
    name: 'Batch caching',

    test_update_from_model_caches: function() {
        /* update_from_model caches the settings in the module.batches. */
        var lp_cache = {
            context: {
                resource_type_link: 'http://foo_type',
                web_link: 'http://foo/bar'
            },
            mustache_model: {
                foo: 'bar'
            }
        };
        var template = "<ol>" +
            "{{#item}}<li>{{name}}</li>{{/item}}</ol>";
        var navigator = new module.ListingNavigator(window.location, lp_cache,
                                                    template);
        var key = module.ListingNavigator.get_batch_key({
            order_by: "intensity",
            memo: 'memo1',
            forwards: true,
            start: 5
        });
        var batch = {
            order_by: 'intensity',
            memo: 'memo1',
            forwards: true,
            start: 5,
            mustache_model: {item: [
                {name: 'first'},
                {name: 'second'}
            ]}}
        navigator.update_from_model(batch);
        Y.lp.testing.assert.assert_equal_structure(
            batch, navigator.batches[key]);
    },
    test_get_batch_key: function(){
        var key = module.ListingNavigator.get_batch_key({
            order_by: 'order_by1',
            memo: 'memo1',
            forwards: true,
            start: 5});
        Y.Assert.areSame('["order_by1","memo1",true,5]', key);
    }
}));

suite.add(new Y.Test.Case({
    name: 'get_query',

    test_get_query: function() {
        // get_query returns the query portion of a URL in structured form.
        var query = module.get_query('http://yahoo.com?me=you&a=b&a=c');
        Y.lp.testing.assert.assert_equal_structure(
            {me: 'you', a: ['b', 'c']}, query);
    }
}));


suite.add(new Y.Test.Case({
    name: 'get_batch_url',

    test_get_batch_query_orderby: function(){
        var navigator = new module.ListingNavigator('?param=1');
        var query = navigator.get_batch_query({order_by: 'importance'});
        Y.Assert.areSame('importance', query.orderby);
        Y.Assert.areSame(1, query.param);
    },
    test_get_batch_query_memo: function(){
        var navigator = new module.ListingNavigator('?param=foo');
        var query = navigator.get_batch_query({memo: 'pi'});
        Y.Assert.areSame('pi', query.memo);
        Y.Assert.areSame('foo', query.param);
    },
    test_get_batch_null_memo: function(){
        var navigator = new module.ListingNavigator('?memo=foo');
        var query = navigator.get_batch_query({memo: null});
        Y.Assert.areSame(undefined, query.memo);
    },
    test_get_batch_query_forwards: function(){
        var navigator = new module.ListingNavigator(
            '?param=pi&direction=backwards');
        var query = navigator.get_batch_query({forwards: true});
        Y.Assert.areSame('pi', query.param);
        Y.Assert.areSame(undefined, query.direction);
    },
    test_get_batch_query_backwards: function(){
        var navigator = new module.ListingNavigator('?param=pi');
        var query = navigator.get_batch_query({forwards: false});
        Y.Assert.areSame('pi', query.param);
        Y.Assert.areSame('backwards', query.direction);
    },
    test_get_batch_query_start: function(){
        var navigator = new module.ListingNavigator('?start=pi');
        var query = navigator.get_batch_query({});
        Y.Assert.areSame(undefined, query.start);
        query = navigator.get_batch_query({start: 1});
        Y.Assert.areSame(1, query.start);
        query = navigator.get_batch_query({start: null});
        Y.lp.testing.assert.assert_equal_structure({}, query);
    }
}));

var get_navigator = function(url){
    var mock_io = new Y.lp.testing.mockio.MockIo();
    lp_cache = {
        context: {
            resource_type_link: 'http://foo_type',
            web_link: 'http://foo/bar'
        },
        next: {
            memo: 467,
            start: 500
        },
        prev: {
            memo: 457,
            start: 400
        },
        order_by: 'foo',
        last_start: 23
    };
    return new module.ListingNavigator(url, lp_cache, null, null, mock_io);
};

suite.add(new Y.Test.Case({
    name: 'navigation',
    test_last_batch: function(){
        var navigator = get_navigator(
            '?memo=pi&direction=backwards&start=57');
        navigator.last_batch();
        Y.Assert.areSame(
            '/bar/+bugs/++model++?orderby=foo&memo=&start=23&' +
            'direction=backwards',
            navigator.io_provider.last_request.url);
    },
    test_first_batch: function(){
        var navigator = get_navigator('?memo=pi&start=26');
        navigator.first_batch();
        Y.Assert.areSame(
            '/bar/+bugs/++model++?orderby=foo&start=0',
            navigator.io_provider.last_request.url);
    },
    test_next_batch: function(){
        var navigator = get_navigator('?memo=pi&start=26');
        navigator.next_batch();
        Y.Assert.areSame(
            '/bar/+bugs/++model++?orderby=foo&memo=467&start=500',
            navigator.io_provider.last_request.url);
    },
    test_prev_batch: function(){
        var navigator = get_navigator('?memo=pi&start=26');
        navigator.prev_batch();
        Y.Assert.areSame(
            '/bar/+bugs/++model++?orderby=foo&memo=457&start=400&' +
            'direction=backwards',
            navigator.io_provider.last_request.url);
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
