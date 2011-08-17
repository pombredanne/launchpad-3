/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'lp.testing.iorecorder', 'test', 'console',
          'lp.client', function(Y) {

var suite = new Y.Test.Suite("lp.code.requestbuild_overlay Tests");

var module = Y.lp.code.requestbuild_overlay;

suite.add(new Y.Test.Case({
    name: "lp.code.requestbuild_overlay.RequestResponseHandler",

    setUp: function() {
    },

    test_normalize_uri: function() {
        var Handler = new module.RequestResponseHandler();
    },


}));

Y.lp.testing.Runner.run(suite);

});
