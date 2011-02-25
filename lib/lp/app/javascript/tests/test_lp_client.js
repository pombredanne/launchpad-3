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
