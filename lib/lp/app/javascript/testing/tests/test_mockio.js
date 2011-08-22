/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('test', 'console', 'node-event-simulate',
          'lp.testing.mockio', 'lp.testing.runner', function(Y) {

var suite = new Y.Test.Suite("lp.testing.mockio Tests");

var module = Y.lp.testing.mockio;

suite.add(new Y.Test.Case({
    name: "lp.testing.mokio",

    setUp: function() {
    },

}));

Y.lp.testing.Runner.run(suite);

});
