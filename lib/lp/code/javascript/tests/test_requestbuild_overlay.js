/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'lp.testing.iorecorder', 'test', 'console',
          'node-event-simulate', 'lp.client',
          'lp.code.requestbuild_overlay', function(Y) {

var suite = new Y.Test.Suite("lp.code.requestbuild_overlay Tests");

var module = Y.lp.code.requestbuild_overlay;

suite.add(new Y.Test.Case({
    name: "lp.code.requestbuild_overlay",

    setUp: function() {
    },

    test_requestbuild: function() {
        var build_now_link = Y.one('#request-daily-build');
        build_now_link.removeClass('unseen');
        module.connect_requestdailybuild();
        build_now_link.simulate('click');
    },



}));

Y.lp.testing.Runner.run(suite);

});
