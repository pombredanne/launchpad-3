/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'lp.testing.mockio', 'test', 'console',
          'lp.client', 'escape', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("lp.client Tests");

suite.add(new Y.Test.Case({
    name: "lp.client",

    setUp: function() {
    },

    test_normalize_uri: function() {
        var normalize = Y.lp.client.normalize_uri;
        Assert.areEqual(
            normalize("http://www.example.com/api/devel/foo"),
            "/api/devel/foo");
        Assert.areEqual(
            normalize("http://www.example.com/foo/bar"), "/foo/bar");
        Assert.areEqual(
            normalize("/foo/bar"), "/api/devel/foo/bar");
        Assert.areEqual(
            normalize("/api/devel/foo/bar"), "/api/devel/foo/bar");
        Assert.areEqual(
            normalize("foo/bar"), "/api/devel/foo/bar");
        Assert.areEqual(
            normalize("api/devel/foo/bar"), "/api/devel/foo/bar");
    },

    test_get_io_provider__default: function() {
        var undefined_provider,
            io_provider = Y.lp.client.get_io_provider(undefined_provider);
        Assert.areSame(Y, io_provider);
    },

    test_get_io_provider__mockio: function() {
        // If a mock provider is provided, it is picked as the io_provider.
        var mockio = new Y.lp.testing.mockio.MockIo(),
            io_provider = Y.lp.client.get_io_provider(mockio);
        Assert.areSame(mockio, io_provider);
    },

    test_get_configured_io_provider__default: function() {
        // If no io_provider is configured, Y is the io_provider.
        var io_provider = Y.lp.client.get_configured_io_provider({});
        Assert.areSame(Y, io_provider);
    },

    test_get_configured_io_provider__default_undefined: function() {
        // If no configuration is provided, Y is the io_provider.
        var io_provider = Y.lp.client.get_configured_io_provider();
        Assert.areSame(Y, io_provider);
    },

    test_get_configured_io_provider__mockio: function() {
        // If an io_provider is configured,  it is picked as the io_provider.
        var mockio = new Y.lp.testing.mockio.MockIo(),
            io_provider = Y.lp.client.get_configured_io_provider(
                {io_provider: mockio});
        Assert.areSame(mockio, io_provider);
    },

    test_get_configured_io_provider__different_key: function() {
        // The io_provider can be stored with a different key.
        var mockio = new Y.lp.testing.mockio.MockIo(),
            io_provider = Y.lp.client.get_configured_io_provider(
                {my_io: mockio}, 'my_io');
        Assert.areSame(mockio, io_provider);
    },

    test_append_qs: function() {
        var qs = "";
        qs = Y.lp.client.append_qs(qs, "Pöllä", "Perelló");
        Assert.areEqual("P%C3%83%C2%B6ll%C3%83%C2%A4=Perell%C3%83%C2%B3", qs);
    },

    test_append_qs_with_array: function() {
        // append_qs() appends multiple arguments to the query string
        // when a parameter value is an array.
        var qs = "";
        qs = Y.lp.client.append_qs(qs, "foo", ["bar", "baz"]);
        Assert.areEqual("foo=bar&foo=baz", qs);
        // All values in the array are encoded correctly too.
        qs = Y.lp.client.append_qs(qs, "a&b", ["a+b"]);
        Assert.areEqual("foo=bar&foo=baz&a%26b=a%2Bb", qs);
    },

    test_field_uri: function() {
      var get_field_uri = Y.lp.client.get_field_uri;
      Assert.areEqual(
          get_field_uri("http://www.example.com/api/devel/foo", "field"),
          "/api/devel/foo/field");
      Assert.areEqual(
          get_field_uri("/no/slash", "field"),
          "/api/devel/no/slash/field");
      Assert.areEqual(
          get_field_uri("/has/slash/", "field"),
          "/api/devel/has/slash/field");
    },
    test_view_url: function() {
        entry_repr = {web_link: 'http://example.com/context'};
        var context = new Y.lp.client.Entry(null, entry_repr, null);
        expected = '/context/+myview/++mynamespace++';
        actual = Y.lp.client.get_view_url(context, '+myview', 'mynamespace');
        Assert.areEqual(expected, actual);
    },
    test_get_form_url: function() {
        entry_repr = {web_link: 'http://example.com/context'};
        var context = new Y.lp.client.Entry(null, entry_repr, null);
        expected = '/context/+myview/++form++';
        actual = Y.lp.client.get_form_url(context, '+myview');
        Assert.areEqual(expected, actual);
    },
    test_load_model: function(){
        var mockio = new Y.lp.testing.mockio.MockIo();
        Assert.areEqual(0, mockio.requests.length);
        var mylist = [];
        var config = {
            io_provider: mockio,
            on: {
                success: Y.bind(mylist.push, mylist)
            }
        };
        var entry_repr = {web_link: 'http://example.com/context'};
        var client = new Y.lp.client.Launchpad();
        var context = new Y.lp.client.Entry(client, entry_repr, null);
        Y.lp.client.load_model(context, '+myview', config);
        Assert.areEqual(
            '/context/+myview/++model++', mockio.last_request.url);
        mockio.success({
            responseText:
                '{"boolean": true, "entry": {"resource_type_link": "foo"}}',
            responseHeaders: {'Content-Type': 'application/json'}
        });
        var result = mylist[0];
        Assert.areSame(true, result.boolean);
        Assert.isInstanceOf(Y.lp.client.Entry, result.entry);
        Assert.areSame('foo', result.entry.get('resource_type_link'));
    },
    test_get_success_callback: function() {
      var mockio = new Y.lp.testing.mockio.MockIo();
      var mylist = [];
      var client = new Y.lp.client.Launchpad({io_provider: mockio});
      client.get('/people', {on:{success: Y.bind(mylist.push, mylist)}});
      Assert.areEqual('/api/devel/people', mockio.last_request.url);
      mockio.success({
        responseText:
        '{"entry": {"resource_type_link": "foo"}}',
        responseHeaders: {'Content-Type': 'application/json'}
      });
      var result = mylist[0];
      Assert.isInstanceOf(Y.lp.client.Entry, result.entry);
      Assert.areSame('foo', result.entry.get('resource_type_link'));
    },
    test_get_failure_callback: function() {
      var mockio = new Y.lp.testing.mockio.MockIo();
      var mylist = [];
      var client = new Y.lp.client.Launchpad({io_provider: mockio});
      client.get(
        '/people',
        {on:{failure: function(){mylist.push(Array.prototype.slice.call(arguments))}}});
      mockio.failure({status: 503});
      var result = mylist[0];
      Assert.areSame(503, result[1].status);
      Assert.areSame('/api/devel/people', result[2][1])
    },
    test_named_post_success_callback: function() {
      var mockio = new Y.lp.testing.mockio.MockIo();
      var mylist = [];
      var client = new Y.lp.client.Launchpad({io_provider: mockio});
      client.named_post(
        '/people', 'newTeam', {on:{success: Y.bind(mylist.push, mylist)}})
      Assert.areEqual('/api/devel/people', mockio.last_request.url);
      Assert.areEqual('ws.op=newTeam', mockio.last_request.config.data)
      Assert.areEqual('POST', mockio.last_request.config.method)
      mockio.success({
        responseText:
        '{"entry": {"resource_type_link": "foo"}}',
        responseHeaders: {'Content-Type': 'application/json'}
      });
      var result = mylist[0];
      Assert.isInstanceOf(Y.lp.client.Entry, result.entry);
      Assert.areSame('foo', result.entry.get('resource_type_link'));
    },
    test_wrap_resource_nested_mapping: function() {
        // wrap_resource produces mappings of plain object literals. These can
        // be nested and have Entries in them.
        var foo = {
            baa: {},
            bar: {
                baz: {
                    resource_type_link: 'qux'}
            }
        };
        foo = new Y.lp.client.Launchpad().wrap_resource(null, foo);
        Y.Assert.isInstanceOf(Y.lp.client.Entry, foo.bar.baz);
    },
    test_wrap_resource_nested_array: function() {
        // wrap_resource produces arrays of array literals. These can
        // be nested and have Entries in them.
        var foo = [[{resource_type_link: 'qux'}]];
        foo = new Y.lp.client.Launchpad().wrap_resource(null, foo);
        Y.Assert.isInstanceOf(Y.lp.client.Entry, foo[0][0]);
    },
    test_wrap_resource_creates_array: function() {
        // wrap_resource creates new arrays, rather than reusing the existing
        // one.
        var foo = ['a'];
        var bar = new Y.lp.client.Launchpad().wrap_resource(null, foo);
        Y.Assert.areNotSame(foo, bar);
    },
    test_wrap_resource_creates_mapping: function() {
        // wrap_resource creates new mappings, rather than reusing the
        // existing one.
        var foo = {a: 'b'};
        var bar = new Y.lp.client.Launchpad().wrap_resource(null, foo);
        Y.Assert.areNotSame(foo, bar);
    },
    test_wrap_resource_null: function() {
        // wrap_resource handles null correctly.
        var foo = {
            bar: null
        };
        foo = new Y.lp.client.Launchpad().wrap_resource(null, foo);
        Y.Assert.isNull(foo.bar);
    }
}));

suite.add(new Y.Test.Case({
    name: "update cache",

    setUp: function() {
        window.LP = {
          cache: {
             context: {
              'first': "Hello",
              'second': true,
              'third': 42,
              'fourth': "Unaltered",
              'self_link': Y.lp.client.get_absolute_uri("a_self_link")
            }
          }};
    },

    tearDown: function() {
        delete window.LP;
    },

    test_update_cache: function() {
        // Make sure that the cached objects are in fact updated.
        var entry_repr = {
          'first': "World",
          'second': false,
          'third': 24,
          'fourth': "Unaltered",
          'self_link': Y.lp.client.get_absolute_uri("a_self_link")
        };
        var entry = new Y.lp.client.Entry(null, entry_repr, "a_self_link");
        Y.lp.client.update_cache(entry);
        Assert.areEqual("World", LP.cache.context.first);
        Assert.areEqual(false, LP.cache.context.second);
        Assert.areEqual(24, LP.cache.context.third);
        Assert.areEqual("Unaltered", LP.cache.context.fourth);
      },

    test_getHTML: function() {
        // Make sure that the getHTML method works as expected.
        var entry_repr = {
          'first': "Hello",
          'second': "World",
          'self_link': Y.lp.client.get_absolute_uri("a_self_link"),
          'lp_html': {'first': "<p>Hello</p><p>World</p>"}
        };
        var entry = new Y.lp.client.Entry(null, entry_repr, "a_self_link");
        Assert.areEqual(
            "<p>Hello</p><p>World</p>",
            entry.getHTML('first').get('innerHTML'));
        // If there is no html representation, null is returned.
        Assert.areEqual(null, entry.getHTML('second'));
      },

    test_update_cache_raises_events: function() {
        // Check that the object changed event is raised.
        var raised_event = null;
        var handle = Y.on('lp:context:changed', function(e) {
            raised_event = e;
          });
        var entry_repr = {
          'first': "World",
          'second': false,
          'third': 24,
          'fourth': "Unaltered",
          'self_link': Y.lp.client.get_absolute_uri("a_self_link")
        };
        var entry = new Y.lp.client.Entry(null, entry_repr, "a_self_link");
        Y.lp.client.update_cache(entry);
        handle.detach();
        Y.ArrayAssert.itemsAreEqual(
            ['first','second','third'], raised_event.fields_changed);
        Assert.areEqual(entry, raised_event.entry);
      },

    test_update_cache_raises_attribute_events: function() {
        // Check that the object attribute changed events are raised.
        var first_event = null;
        var second_event = null;
        var third_event = null;
        var fourth_event = null;
        var first_handle = Y.on('lp:context:first:changed', function(e) {
            first_event = e;
          });
        var second_handle = Y.on('lp:context:second:changed', function(e) {
            second_event = e;
          });
        var third_handle = Y.on('lp:context:third:changed', function(e) {
            third_event = e;
          });
        var fourth_handle = Y.on('lp:context:fourth:changed', function(e) {
            fourth_event = e;
          });
        var entry_repr = {
          'first': "World<boo/>",
          'second': false,
          'third': 24,
          'fourth': "Unaltered",
          'self_link': Y.lp.client.get_absolute_uri("a_self_link"),
          'lp_html': {'first': "<p>World html<boo/></p>"}
        };
        var entry = new Y.lp.client.Entry(null, entry_repr, "a_self_link");
        Y.lp.client.update_cache(entry);
        first_handle.detach();
        second_handle.detach();
        third_handle.detach();
        fourth_handle.detach();

        Assert.areEqual('first', first_event.name);
        Assert.areEqual('Hello', first_event.old_value);
        Assert.areEqual('World<boo/>', first_event.new_value);
        Assert.areEqual(
            '<p>World html<boo></boo></p>',
            first_event.new_value_html.get('innerHTML'));
        Assert.areEqual(entry, first_event.entry);

        Assert.areEqual('second', second_event.name);
        Assert.areEqual(true, second_event.old_value);
        Assert.areEqual(false, second_event.new_value);
        Assert.areEqual(entry, second_event.entry);

        Assert.areEqual('third', third_event.name);
        Assert.areEqual(42, third_event.old_value);
        Assert.areEqual(24, third_event.new_value);
        Assert.areEqual(entry, third_event.entry);

        Assert.isNull(fourth_event);
      },

    test_update_cache_different_object: function() {
        // Check that the object is not modified if the entry has a different
        // link.
        var entry_repr = {
          'first': "World",
          'second': false,
          'third': 24,
          'fourth': "Unaltered",
          'self_link': Y.lp.client.get_absolute_uri("different_link")
        };
        var entry = new Y.lp.client.Entry(null, entry_repr, "different_link");
        Y.lp.client.update_cache(entry);
        Assert.areEqual("Hello", LP.cache.context.first);
        Assert.areEqual(true, LP.cache.context.second);
        Assert.areEqual(42, LP.cache.context.third);
        Assert.areEqual("Unaltered", LP.cache.context.fourth);
      }
}));

suite.add(new Y.Test.Case({
    name: "lp.client.notifications",

    setUp: function() {
        this.client = new Y.lp.client.Launchpad();
        this.args=[this.client, null, this._on_success, false];
        this.response = new Y.lp.testing.mockio.MockHttpResponse();
        this.response.setResponseHeader('Content-Type', 'application/json');
    },

    _on_success: function(entry) {
    },

    _checkNotificationNode: function(node_class, node_text) {
        var node = Y.one('div#request-notifications div'+node_class);
        Assert.areEqual(node_text, node.get("innerHTML"));
    },

    _checkNoNotificationNode: function(node_class) {
        var node = Y.one('div#request-notifications div'+node_class);
        Assert.isNull(node);
    },

    test_display_notifications: function() {
        var notifications = '[ [10, "A debug"], [20, "An info"] ]';
        this.response.setResponseHeader(
                'X-Lazr-Notifications', notifications);
        Y.lp.client.wrap_resource_on_success(null, this.response, this.args);
        this._checkNotificationNode('.debug.message', 'A debug');
        this._checkNotificationNode('.informational.message', 'An info');

        // Any subsequent request should preserve existing notifications.
        var new_notifications = '[ [30, "A warning"], [40, "An error"] ]';
        this.response.setResponseHeader(
                'X-Lazr-Notifications', new_notifications);
        Y.lp.client.wrap_resource_on_success(null, this.response, this.args);
        this._checkNotificationNode('.debug.message', 'A debug');
        this._checkNotificationNode('.informational.message', 'An info');
        this._checkNotificationNode('.warning.message', 'A warning');
        this._checkNotificationNode('.error.message', 'An error');
    },

    test_remove_notifications: function() {
        // Make some notifications that will be removed.
        var notifications = '[ [10, "A debug"], [20, "An info"] ]';
        this.response.setResponseHeader(
                'X-Lazr-Notifications', notifications);
        Y.lp.client.wrap_resource_on_success(null, this.response, this.args);

        // If the notifications header is just the string "null", then the
        // current notifications are removed.
        this.response.setResponseHeader('X-Lazr-Notifications', "null");
        Y.lp.client.wrap_resource_on_success(null, this.response, this.args);
        this._checkNoNotificationNode('.debug.message');
        this._checkNoNotificationNode('.informational.message');
    },

    test_notifications_not_removed: function() {
        // Make some notifications that will be removed.
        var notifications = '[ [10, "A debug"], [20, "An info"] ]';
        this.response.setResponseHeader(
                'X-Lazr-Notifications', notifications);
        Y.lp.client.wrap_resource_on_success(null, this.response, this.args);

        // If the response does not include a notifications header, then any
        // pre-existing notifiactions are not removed.
        this.response.setResponseHeader('X-Lazr-Notifications', null);
        Y.lp.client.wrap_resource_on_success(null, this.response, this.args);
        this._checkNotificationNode('.debug.message', 'A debug');
        this._checkNotificationNode('.informational.message', 'An info');
    }

}));

Y.lp.testing.Runner.run(suite);

});
