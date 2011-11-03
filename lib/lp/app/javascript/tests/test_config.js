/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lp.baseconfig.test', function(Y) {

var baseconfig_test = Y.namespace('lp.baseconfig.test');

var suite = new Y.Test.Suite('BaseConfig Tests');

var Assert = Y.Assert;

suite.add(new Y.Test.Case({

    name: 'baseconfig_widget_tests',

    tearDown: function() {
        if (Y.Lang.isValue(this.baseconfig)) {
            this.baseconfig.destroy();
        }
    },

    test_base_config_render: function() {
        // The div rendered should have sprite and config
        // class names added to it.
        Y.Node.create('<div></div>').set('id', 'test-div');
        var baseconfig = new Y.lp.config.BaseConfig({
            srcNode: Y.one('#test-div')
        });
        baseconfig.render();
        var baseconfig_content = Y.one('.yui3-baseconfig-content');
        Assert.isTrue(baseconfig_content.hasClass('sprite'));
        Assert.isTrue(baseconfig_content.hasClass('config'));
    }

}));

baseconfig_test.suite = suite;

}, '0.1', {'requires': ['test', 'node-event-simulate', 'lp.config']});
