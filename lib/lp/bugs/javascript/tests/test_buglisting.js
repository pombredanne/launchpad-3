YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.buglisting', 'lp.testing.mockio',
           'lp.testing.assert',
           function(Y) {

var suite = new Y.Test.Suite("lp.bugs.buglisting Tests");
var module = Y.lp.bugs.buglisting;

/**
 * Set the HTML fixture to the desired value.
 */
var set_fixture = function(value){
    var fixture = Y.one('#fixture');
    fixture.set('innerHTML', value);
};

suite.add(new Y.Test.Case({
    name: 'rendertable',

    setUp: function () {
        this.MY_NAME = "ME";
        window.LP = { links: { me: "/~" + this.MY_NAME } };
    },

    tearDown: function() {
        delete window.LP;
        set_fixture('');
    },

    test_rendertable_no_client_listing: function() {
        // Rendering should not error with no #client-listing.
        module.rendertable();
    },
    test_rendertable: function() {
        // Rendering should work with #client-listing supplied.
        set_fixture('<div id="client-listing"></div>');
        window.LP.cache = {
            mustache_model: {
                foo: 'bar'
            }
        };
        window.LP.mustache_listings = "{{foo}}";
        module.rendertable();
        Y.Assert.areEqual('bar', Y.one('#client-listing').get('innerHTML'));
    }
}));

suite.add(new Y.Test.Case({
    name: 'update_listing',

    setUp: function () {
        this.MY_NAME = "ME";
        var lp_client = new Y.lp.client.Launchpad();
        window.LP = { links: { me: "/~" + this.MY_NAME } };
        set_fixture('<div id="client-listing"></div>');
        window.LP.cache = {
            context: {
                resource_type_link: 'http://foo_type',
                web_link: 'http://foo/bar'
            },
            mustache_model: {
                foo: 'bar'
            }
        };
        window.LP.mustache_listings = "<ol>" +
            "{{#item}}<li>{{name}}</li>{{/item}}</ol>";
    },
    tearDown: function() {
        delete window.LP;
        module.batches = {};
    },
    get_intensity_listing: function(){
        mock_io = new Y.lp.testing.mockio.MockIo();
        module.update_listing('intensity', {io_provider: mock_io});
        Y.Assert.areEqual('',
            Y.one('#client-listing').get('innerHTML'));
        mock_io.last_request.successJSON({mustache_model:
            {item: [
                {name: 'first'},
                {name: 'second'}
            ]}
        });
        return mock_io;
    },
    test_update_listing: function() {
        /* update_listing retrieves a listing for the new ordering and
         * displays it */
        mock_io = this.get_intensity_listing();
        Y.Assert.areEqual('<ol><li>first</li><li>second</li></ol>',
            Y.one('#client-listing').get('innerHTML'));
        Y.Assert.areEqual('/bar/+bugs/++model++?orderby=intensity',
            mock_io.last_request.url);
    },
    test_update_listing_uses_cache: function() {
        /* update_listing will use the cached value instead of making a second
         * AJAX request. */
        mock_io = this.get_intensity_listing();
        Y.Assert.areEqual(1, mock_io.requests.length);
        module.update_listing('intensity', {io_provider: mock_io});
        Y.Assert.areEqual(1, mock_io.requests.length);
    }
}));
suite.add(new Y.Test.Case({
    name: 'Batch caching',

    setUp: function () {
        this.MY_NAME = "ME";
        var lp_client = new Y.lp.client.Launchpad();
        window.LP = { links: { me: "/~" + this.MY_NAME } };
        set_fixture('<div id="client-listing"></div>');
        window.LP.cache = {
            context: {
                resource_type_link: 'http://foo_type',
                web_link: 'http://foo/bar'
            },
            mustache_model: {
                foo: 'bar'
            }
        };
        window.LP.mustache_listings = "<ol>" +
            "{{#item}}<li>{{name}}</li>{{/item}}</ol>";
    },
    tearDown: function() {
        delete window.LP;
        module.batches = {};
    },
    test_update_from_model_caches: function() {
        /* update_from_model caches the settings in the module.batches. */
        module.update_from_model('intensity', {mustache_model: {item: [
                {name: 'first'},
                {name: 'second'}
            ]}});
        Y.lp.testing.assert.assert_equal_structure(
            {item: [{name: 'first'}, {name: 'second'}]},
            module.batches.intensity);
    }
}));

suite.add(new Y.Test.Case({
    name: 'get_query',

    setUp: function () {
    },
    tearDown: function() {
        delete window.LP;
    },
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
        var query = module.get_batch_query(
            '?memo=1', {order_by: 'importance'});
        Y.Assert.areSame(1, query.memo);
        Y.Assert.areSame('importance', query.orderby);
    },
    test_get_batch_query_memo: function(){
        var query = module.get_batch_query(
            '?orderby=foo', {memo: 'pi'});
        Y.Assert.areSame('pi', query.memo);
        Y.Assert.areSame('foo', query.orderby);
    },
    test_get_batch_query_forward: function(){
        var query = module.get_batch_query(
            '?memo=pi&direction=reverse', {forward: true});
        Y.Assert.areSame('pi', query.memo);
        Y.Assert.areSame(undefined, query.direction);
    },
    test_get_batch_query_reverse: function(){
        var query = module.get_batch_query(
            '?memo=pi', {forward: false});
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
