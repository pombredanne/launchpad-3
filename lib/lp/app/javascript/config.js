/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().add('lp.config', function(Y) {
    /**
     * @module lp.config
     */
    function BaseConfig() {
        BaseConfig.superclass.constructor.apply(this, arguments);
    }

    BaseConfig.NAME = 'baseconfig';

    BaseConfig.ATTRS = {
    };

    Y.extend(BaseConfig, Y.Widget, {

        renderUI: function() {
            var content = this.get('contentBox');
            content.addClass('sprite');
            content.addClass('config');
        }

    });

    var config = Y.namespace('lp.config');
    config.BaseConfig = BaseConfig;

}, '0.1', {'requires': ['widget']});
