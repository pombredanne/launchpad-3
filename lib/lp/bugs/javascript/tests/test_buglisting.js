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
    test_sets_search_params: function() {
        // search_parms includes all query values that don't control batching
        var navigator = new module.ListingNavigator({
            current_url: 'http://yahoo.com?foo=bar&start=1&memo=2&' +
                'direction=3&orderby=4',
            cache: {next: null, prev: null}});
        Y.lp.testing.assert.assert_equal_structure(
            {foo: 'bar'}, navigator.get('search_params'));
    },
    test_cleans_visibility_from_current_batch: function() {
        // When initial batch is handled, field visibility is stripped.
        var navigator = new module.ListingNavigator({
            current_url: '',
            cache: {
                field_visibility: {show_item: true},
                mustache_model: {bugtasks: [{show_item: true} ] },
                next: null,
                prev: null
            }
        });
        bugtask = navigator.get_current_batch().mustache_model.bugtasks[0];
        Y.Assert.isFalse(bugtask.hasOwnProperty('show_item'));
    },
    test_cleans_visibility_from_new_batch: function() {
        // When new batch is handled, field visibility is stripped.
        var bugtask;
        var target = Y.Node.create('<div id="client-listing"></div>');
        var model = {
            mustache_model: {bugtasks: []},
            memo: 1,
            next: null,
            prev: null,
            field_visibility: {},
            field_visibility_defaults: {show_item: true}
        };
        var navigator = new module.ListingNavigator({
            current_url: '',
            cache: model,
            template: '',
            target: target
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
        navigator.update_from_new_model(query, batch);
        bugtask = navigator.get_current_batch().mustache_model.bugtasks[0];
        Y.Assert.isFalse(bugtask.hasOwnProperty('show_item'));
    }
}));

suite.add(new Y.Test.Case({
    name: 'render',

    tearDown: function() {
        Y.one('#fixture').setContent('');
    },

    get_render_navigator: function() {
        var target = Y.Node.create('<div id="client-listing"></div>');
        var lp_cache = {
            mustache_model: {
                bugtasks: [{foo: 'bar', show_foo: true}]
            },
            next: null,
            prev: null,
            start: 5,
            total: 256,
            field_visibility: {show_foo: true},
            field_visibility_defaults: {show_foo: false}
        };
        var template = "{{#bugtasks}}{{#show_foo}}{{foo}}{{/show_foo}}" +
            "{{/bugtasks}}";
        var navigator =  new module.ListingNavigator({
            cache: lp_cache,
            template: template,
            target: target
        });
        var index = Y.Node.create(
            '<div><strong>3</strong> &rarr; <strong>4</strong>' +
            ' of 512 results</div>');
        navigator.get('navigation_indices').push(index);
        navigator.get('backwards_navigation').push(
            Y.Node.create('<div></div>'));
        navigator.get('forwards_navigation').push(
            Y.Node.create('<div></div>'));
        return navigator;
    },
    test_render: function() {
        // Rendering should work with #client-listing supplied.
        var navigator = this.get_render_navigator();
        navigator.render();
        Y.Assert.areEqual('bar', navigator.get('target').getContent());
    },
    /**
     * render_navigation should disable "previous" and "first" if there is
     * no previous batch (i.e. we're at the beginning.)
     */
    test_render_navigation_disables_backwards_navigation_if_no_prev:
    function() {
        var navigator = this.get_render_navigator();
        var action = navigator.get('backwards_navigation').item(0);
        navigator.render_navigation();
        Y.Assert.isTrue(action.hasClass('inactive'));
    },
    /**
     * render_navigation should enable "previous" and "first" if there is
     * a previous batch (i.e. we're not at the beginning.)
     */
    test_render_navigation_enables_backwards_navigation_if_prev:
    function() {
        var navigator = this.get_render_navigator();
        var action = navigator.get('backwards_navigation').item(0);
        action.addClass('inactive');
        navigator.get_current_batch().prev = {
            start: 1, memo: 'pi'
        };
        navigator.render_navigation();
        Y.Assert.isFalse(action.hasClass('inactive'));
    },
    /**
     * render_navigation should disable "next" and "last" if there is
     * no next batch (i.e. we're at the end.)
     */
    test_render_navigation_disables_forwards_navigation_if_no_next:
    function() {
        var navigator = this.get_render_navigator();
        var action = navigator.get('forwards_navigation').item(0);
        navigator.render_navigation();
        Y.Assert.isTrue(action.hasClass('inactive'));
    },
    /**
     * render_navigation should enable "next" and "last" if there is a next
     * batch (i.e. we're not at the end.)
     */
    test_render_navigation_enables_forwards_navigation_if_next: function() {
        var navigator = this.get_render_navigator();
        var action = navigator.get('forwards_navigation').item(0);
        action.addClass('inactive');
        navigator.get_current_batch().next = {
            start: 1, memo: 'pi'
        };
        navigator.render_navigation();
        Y.Assert.isFalse(action.hasClass('inactive'));
    },
    /**
     * linkify_navigation should convert previous, next, first last into
     * hyperlinks, while retaining the original content.
     */
    test_linkify_navigation: function()  {
        Y.one('#fixture').setContent(
            '<span class="previous">PreVious</span>' +
            '<span class="next">NeXt</span>' +
            '<span class="first">FiRST</span>' +
            '<span class="last">lAst</span>');
        module.linkify_navigation();
        function checkNav(selector, content) {
            var node = Y.one(selector);
            Y.Assert.areEqual('a', node.get('tagName').toLowerCase());
            Y.Assert.areEqual(content, node.getContent());
            Y.Assert.areEqual('#', node.get('href').substr(-1, 1));
        }
        checkNav('.previous', 'PreVious');
        checkNav('.next', 'NeXt');
        checkNav('.first', 'FiRST');
        checkNav('.last', 'lAst');
    },
    /**
     * Render should update the navigation_indices with the result info.
     */
    test_render_navigation_indices: function() {
        var navigator = this.get_render_navigator();
        var index = navigator.get('navigation_indices').item(0);
        Y.Assert.areEqual(
            '<strong>3</strong> \u2192 <strong>4</strong> of 512 results',
            index.getContent());
        navigator.render();
        Y.Assert.areEqual(
            '<strong>6</strong> \u2192 <strong>6</strong> of 256 results',
            index.getContent());
    }
}));

suite.add(new Y.Test.Case({
    name: 'first_batch',

    /**
     * Return a ListingNavigator ordered by 'intensity'
     */
    get_intensity_listing: function() {
        mock_io = new Y.lp.testing.mockio.MockIo();
        lp_cache = {
            context: {
                resource_type_link: 'http://foo_type',
                web_link: 'http://foo/bar'
            },
            mustache_model: {
                foo: 'bar',
                bugtasks: []
            },
            next: null,
            prev: null,
            field_visibility: {},
            field_visibility_defaults: {}
        };
        var target = Y.Node.create('<div id="client-listing"></div>');
        var navigator = new module.ListingNavigator({
            current_url:
                "http://yahoo.com?start=5&memo=6&direction=backwards",
            cache: lp_cache,
            template: "<ol>" + "{{#item}}<li>{{name}}</li>{{/item}}</ol>",
            target: target,
            io_provider: mock_io
        });
        navigator.first_batch('intensity');
        Y.Assert.areEqual('', navigator.get('target').getContent());
        mock_io.last_request.successJSON({
            context: {
                resource_type_link: 'http://foo_type',
                web_link: 'http://foo/bar'
            },
            mustache_model:
            {
                item: [
                {name: 'first'},
                {name: 'second'}],
                bugtasks: []
            },
            order_by: 'intensity',
            start: 0,
            forwards: true,
            memo: null,
            next: null,
            prev: null
        });
        return navigator;
    },
    test_first_batch: function() {
        /* first_batch retrieves a listing for the new ordering and
         * displays it */
        var navigator = this.get_intensity_listing();
        var mock_io = navigator.get('io_provider');
        Y.Assert.areEqual('<ol><li>first</li><li>second</li></ol>',
            navigator.get('target').getContent());
        Y.Assert.areEqual('/bar/+bugs/++model++?orderby=intensity&start=0',
            mock_io.last_request.url);
    },
    test_first_batch_uses_cache: function() {
        /* first_batch will use the cached value instead of making a
         * second AJAX request. */
        var navigator = this.get_intensity_listing();
        Y.Assert.areEqual(1, navigator.get('io_provider').requests.length);
        navigator.first_batch('intensity');
        Y.Assert.areEqual(1, navigator.get('io_provider').requests.length);
    },
    test_io_error: function() {
        var overlay_node;
        var navigator = this.get_intensity_listing();
        navigator.first_batch('failure');
        navigator.get('io_provider').failure();
        overlay_node = Y.one('.yui3-lazr-formoverlay-errors');
        Y.Assert.isTrue(Y.Lang.isValue(overlay_node));
    }
}));

suite.add(new Y.Test.Case({
    name: 'Batch caching',

    test_update_from_new_model_caches: function() {
        /* update_from_new_model caches the settings in the module.batches. */
        var lp_cache = {
            context: {
                resource_type_link: 'http://foo_type',
                web_link: 'http://foo/bar'
            },
            mustache_model: {
                foo: 'bar'
            },
            next: null,
            prev: null,
            field_visibility: {},
            field_visibility_defaults: {}
        };
        var template = "<ol>" +
            "{{#item}}<li>{{name}}</li>{{/item}}</ol>";
        var target = Y.Node.create('<div id="client-listing"></div>');
        var navigator = new module.ListingNavigator({
            current_url: window.location,
            cache: lp_cache,
            template: template,
            target: target
        });
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
            mustache_model: {
                item: [
                    {name: 'first'},
                    {name: 'second'}
                ],
                bugtasks: ['a', 'b', 'c']
            }};
        var query = navigator.get_batch_query(batch);
        navigator.update_from_new_model(query, batch);
        Y.lp.testing.assert.assert_equal_structure(
            batch, navigator.get('batches')[key]);
    },
    /**
     * get_batch_key returns a JSON-serialized list.
     */
    test_get_batch_key: function() {
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

    /**
     * get_batch_query accepts the order_by param.
     */
    test_get_batch_query_orderby: function() {
        var navigator = new module.ListingNavigator({
            current_url: '?param=1',
            cache: {next: null, prev: null}
        });
        var query = navigator.get_batch_query({order_by: 'importance'});
        Y.Assert.areSame('importance', query.orderby);
        Y.Assert.areSame(1, query.param);
    },
    /**
     * get_batch_query accepts the memo param.
     */
    test_get_batch_query_memo: function() {
        var navigator = new module.ListingNavigator({
            current_url: '?param=foo',
            cache: {next: null, prev: null}
        });
        var query = navigator.get_batch_query({memo: 'pi'});
        Y.Assert.areSame('pi', query.memo);
        Y.Assert.areSame('foo', query.param);
    },
    /**
     * When memo is null, query.memo is undefined.
     */
    test_get_batch_null_memo: function() {
        var navigator = new module.ListingNavigator({
            current_url: '?memo=foo',
            cache: {next: null, prev: null}
        });
        var query = navigator.get_batch_query({memo: null});
        Y.Assert.areSame(undefined, query.memo);
    },
    /**
     * If 'forwards' is true, direction does not appear.
     */
    test_get_batch_query_forwards: function() {
        var navigator = new module.ListingNavigator({
            current_url: '?param=pi&direction=backwards',
            cache: {next: null, prev: null}
        });
        var query = navigator.get_batch_query({forwards: true});
        Y.Assert.areSame('pi', query.param);
        Y.Assert.areSame(undefined, query.direction);
    },
    /**
     * If 'forwards' is false, direction is set to backwards.
     */
    test_get_batch_query_backwards: function() {
        var navigator = new module.ListingNavigator({
            current_url: '?param=pi',
            cache: {next: null, prev: null}
        });
        var query = navigator.get_batch_query({forwards: false});
        Y.Assert.areSame('pi', query.param);
        Y.Assert.areSame('backwards', query.direction);
    },
    /**
     * If start is provided, it overrides existing values.
     */
    test_get_batch_query_start: function() {
        var navigator = new module.ListingNavigator({
            current_url: '?start=pi',
            cache: {next: null, prev:null}
        });
        var query = navigator.get_batch_query({});
        Y.Assert.areSame(undefined, query.start);
        query = navigator.get_batch_query({start: 1});
        Y.Assert.areSame(1, query.start);
        query = navigator.get_batch_query({start: null});
        Y.lp.testing.assert.assert_equal_structure({}, query);
    }
}));

var get_navigator = function(url, config) {
    var mock_io = new Y.lp.testing.mockio.MockIo();
    if (config === undefined){
        config = {};
    }
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
    var target = Y.Node.create('<div id="client-listing"></div>');
    return new module.ListingNavigator({
        current_url: url,
        cache: lp_cache,
        io_provider: mock_io,
        target: target,
        template: ''
    });
};

suite.add(new Y.Test.Case({
    name: 'navigation',

    /**
     * last_batch uses memo="", start=navigator.current_batch.last_start,
     * direction=backwards, orderby=navigator.current_batch.order_by.
     */
    test_last_batch: function() {
        var navigator = get_navigator(
            '?memo=pi&direction=backwards&start=57');
        navigator.last_batch();
        Y.Assert.areSame(
            '/bar/+bugs/++model++?orderby=foo&memo=&start=23&' +
            'direction=backwards',
            navigator.get('io_provider').last_request.url);
    },

    /**
     * first_batch omits memo and direction, start=0,
     * orderby=navigator.current_batch.order_by.
     */
    test_first_batch: function() {
        var navigator = get_navigator('?memo=pi&start=26');
        navigator.first_batch();
        Y.Assert.areSame(
            '/bar/+bugs/++model++?orderby=foo&start=0',
            navigator.get('io_provider').last_request.url);
    },

    /**
     * next_batch uses values from current_batch.next +
     * current_batch.ordering.
     */
    test_next_batch: function() {
        var navigator = get_navigator('?memo=pi&start=26');
        navigator.next_batch();
        Y.Assert.areSame(
            '/bar/+bugs/++model++?orderby=foo&memo=467&start=500',
            navigator.get('io_provider').last_request.url);
    },

    /**
     * Calling next_batch when there is none is a no-op.
     */
    test_next_batch_missing: function() {
        var navigator = get_navigator('?memo=pi&start=26', {no_next: true});
        navigator.next_batch();
        Y.Assert.areSame(
            null, navigator.get('io_provider').last_request);
    },

    /**
     * prev_batch uses values from current_batch.prev + direction=backwards
     * and ordering=current_batch.ordering.
     */
    test_prev_batch: function() {
        var navigator = get_navigator('?memo=pi&start=26');
        navigator.prev_batch();
        Y.Assert.areSame(
            '/bar/+bugs/++model++?orderby=foo&memo=457&start=400&' +
            'direction=backwards',
            navigator.get('io_provider').last_request.url);
    },

    /**
     * Calling prev_batch when there is none is a no-op.
     */
    test_prev_batch_missing: function() {
        var navigator = get_navigator(
            '?memo=pi&start=26', {no_prev: true, no_next: true});
        navigator.prev_batch();
        Y.Assert.areSame(
            null, navigator.get('io_provider').last_request);
    }
}));

suite.add(new Y.Test.Case({
    name: 'browser history',

    /**
     * Update from cache generates a change event for the specified batch.
     */
    test_update_from_cache_generates_event: function(){
        var navigator = get_navigator('');
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
        var navigator = get_navigator('');
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
                prev: null
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
        module.ListingNavigator.from_page();
        Y.Assert.areNotSame('http://example.org/', this.getPreviousLink());
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
