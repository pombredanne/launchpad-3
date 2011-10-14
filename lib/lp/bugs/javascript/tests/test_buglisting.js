YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.buglisting', function(Y) {

var suite = new Y.Test.Suite("lp.bugs.buglisting Tests");
var module = Y.lp.bugs.buglisting;

/**
 * Test is_notification_level_shown() for a given set of
 * conditions.
 */
suite.add(new Y.Test.Case({
    name: 'rendertable',

    setUp: function () {
        this.MY_NAME = "ME";
        window.LP = { links: { me: "/~" + this.MY_NAME } };
    },

    tearDown: function() {
        delete window.LP;
        this.set_fixture('');
    },

    set_fixture: function(value) {
        var fixture = Y.one('#fixture');
        fixture.set('innerHTML', value);
    },
    test_rendertable_no_client_listing: function() {
        module.rendertable();
    },
    test_rendertable: function() {
        this.set_fixture('<div id="client-listing"></div>');
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
