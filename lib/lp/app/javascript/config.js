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

    BaseConfig.ATTRS = {
        /**
         * A reference to the anchor element created during renderUI.
         *
         * @attribute anchor
         * @type Y.Node
         * @default null
         */
        anchor: {
            value: null
        }
    };

    Y.extend(BaseConfig, Y.Widget, {

        /**
         * Hook for subclasses to do something when the settings
         * icon is clicked.
         */
        _handleClick: function() {

        },

        /**
         * Hook for subclasses to do work after renderUI.
         */
        _extraRenderUI: function() {

        },

        renderUI: function() {
            var anchor = Y.Node.create(
                '<a></a>').addClass('sprite').addClass('config');
            this.set('anchor', anchor);
            var content = this.get(CONTENT_BOX);
            content.append(anchor);
            this._extraRenderUI();
        },

        bindUI: function() {
            // Do some work here to set up click handlers.
            // Add the a element to ATTRS.
        },

    });

    var config = Y.namespace('lp.config');
    config.BaseConfig = BaseConfig;

}, '0.1', {'requires': ['widget']});
