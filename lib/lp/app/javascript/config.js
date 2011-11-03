/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().add('lp.config', function(Y) {
    /**
     * The config module provides objects for managing the config
     * or settings of a web page or widget.
     *
     * Widgets that want to be accessed from a settings/config
     * icon should extend BaseConfig and provide a callback that
     * will run when the icon is clicked.
     *
     * @module lp.config
     */

    // Constants
    var CONTENT_BOX = 'contentBox';

    /**
     * BaseConfig is the base object that every XXXConfig object
     * should extend.
     *
     * @class BaseConfig
     * @extends Widget
     * @constructor
     */
    function BaseConfig() {
        BaseConfig.superclass.constructor.apply(this, arguments);
    }

    BaseConfig.NAME = 'baseconfig';

    Y.extend(BaseConfig, Y.Widget, {

        renderUI: function() {
            var anchor = Y.Node.create(
                '<a></a>').addClass('sprite').addClass('config');
            var content = this.get(CONTENT_BOX);
            content.append(anchor);
        }

    });

    var config = Y.namespace('lp.config');
    config.BaseConfig = BaseConfig;

}, '0.1', {'requires': ['widget']});
