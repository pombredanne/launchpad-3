YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.buglisting', 'lp.testing.mockio',
           'lp.testing.assert',
           function(Y) {

var suite = new Y.Test.Suite("lp.bugs.buglisting Tests");
var module = Y.lp.bugs.buglisting;

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
    name: 'update_listing',

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
            window.location, lp_cache, "<ol>" +
            "{{#item}}<li>{{name}}</li>{{/item}}</ol>", target, mock_io);
        navigator.update_listing('intensity');
        Y.Assert.areEqual('', navigator.target.get('innerHTML'));
        mock_io.last_request.successJSON({mustache_model:
            {item: [
                {name: 'first'},
                {name: 'second'}
            ]}
        });
        return navigator;
    },
    test_update_listing: function() {
        /* update_listing retrieves a listing for the new ordering and
         * displays it */
        var navigator = this.get_intensity_listing();
        var mock_io = navigator.io_provider;
        Y.Assert.areEqual('<ol><li>first</li><li>second</li></ol>',
            navigator.target.get('innerHTML'));
        Y.Assert.areEqual('/bar/+bugs/++model++?orderby=intensity',
            mock_io.last_request.url);
    },
    test_update_listing_uses_cache: function() {
        /* update_listing will use the cached value instead of making a second
         * AJAX request. */
        var navigator = this.get_intensity_listing();
        Y.Assert.areEqual(1, navigator.io_provider.requests.length);
        navigator.update_listing('intensity');
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
        navigator.update_from_model('intensity', {mustache_model: {item: [
                {name: 'first'},
                {name: 'second'}
            ]}});
        Y.lp.testing.assert.assert_equal_structure(
            {item: [{name: 'first'}, {name: 'second'}]},
            navigator.batches.intensity);
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
        var navigator = new module.ListingNavigator('?memo=1');
        var query = navigator.get_batch_query({order_by: 'importance'});
        Y.Assert.areSame(1, query.memo);
        Y.Assert.areSame('importance', query.orderby);
    },
    test_get_batch_query_memo: function(){
        var navigator = new module.ListingNavigator('?orderby=foo');
        var query = navigator.get_batch_query({memo: 'pi'});
        Y.Assert.areSame('pi', query.memo);
        Y.Assert.areSame('foo', query.orderby);
    },
    test_get_batch_query_forward: function(){
        var navigator = new module.ListingNavigator(
            '?memo=pi&direction=reverse');
        var query = navigator.get_batch_query({forward: true});
        Y.Assert.areSame('pi', query.memo);
        Y.Assert.areSame(undefined, query.direction);
    },
    test_get_batch_query_reverse: function(){
        var navigator = new module.ListingNavigator('?memo=pi');
        var query = navigator.get_batch_query({forward: false});
        Y.Assert.areSame('pi', query.memo);
        Y.Assert.areSame('reverse', query.direction);
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
