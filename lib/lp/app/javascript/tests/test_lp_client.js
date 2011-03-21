/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use('test', 'console', 'lp.client', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("lp.client Tests");

suite.add(new Y.Test.Case({
    name: "lp.client",

    setUp: function() {
    },

    test_normalize_uri: function() {
        var normalize = Y.lp.client.normalize_uri;
        Assert.areEqual(normalize("http://www.example.com/api/devel/foo"), "/api/devel/foo");
        Assert.areEqual(normalize("http://www.example.com/foo/bar"), "/foo/bar");
        Assert.areEqual(normalize("/foo/bar"), "/api/devel/foo/bar");
        Assert.areEqual(normalize("/api/devel/foo/bar"), "/api/devel/foo/bar");
        Assert.areEqual(normalize("foo/bar"), "/api/devel/foo/bar");
        Assert.areEqual(normalize("api/devel/foo/bar"), "/api/devel/foo/bar");
    },

    test_append_qs: function() {
        var qs = "";
        qs = Y.lp.client.append_qs(qs, "Pöllä", "Perelló");
        Assert.areEqual("P%C3%83%C2%B6ll%C3%83%C2%A4=Perell%C3%83%C2%B3", qs);
    },

    test_field_uri: function() {
      var get_field_uri = Y.lp.client.get_field_uri;
      Assert.areEqual(get_field_uri("http://www.example.com/api/devel/foo", "field"),
                      "/api/devel/foo/field");
      Assert.areEqual(get_field_uri("/no/slash", "field"),
                      "/api/devel/no/slash/field");
      Assert.areEqual(get_field_uri("/has/slash/", "field"),
                      "/api/devel/has/slash/field");
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
          'first': "World",
          'second': false,
          'third': 24,
          'fourth': "Unaltered",
          'self_link': Y.lp.client.get_absolute_uri("a_self_link")
        };
        var entry = new Y.lp.client.Entry(null, entry_repr, "a_self_link");
        Y.lp.client.update_cache(entry);
        first_handle.detach();
        second_handle.detach();
        third_handle.detach();
        fourth_handle.detach();

        Assert.areEqual('first', first_event.name);
        Assert.areEqual('Hello', first_event.old_value);
        Assert.areEqual('World', first_event.new_value);
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


// Lock, stock, and two smoking barrels.
var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var yui_console = new Y.Console({
    newestOnTop: false
});
yui_console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
