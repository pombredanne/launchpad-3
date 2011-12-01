/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().add('lp.indicator', function(Y) {

    /**
     * A Overlay overlay-style loading indicator.
     *
     * @module lp.indicator
     */
    function OverlayIndicator() {
        OverlayIndicator.superclass.constructor.apply(this, arguments);
    }

    OverlayIndicator.NAME = 'overlay-indicator';
    OverlayIndicator.NS = 'indicator';

    OverlayIndicator.ATTRS = {

        /**
         * The target of the page this indicator is used for.
         *
         * @attribute target
         * @type Y.Node
         * @default null
         */
        target: {
            value: null
        }
    };

    Y.extend(OverlayIndicator, Y.Widget, {

        /**
         * Set the size of the object to match the
         * target which it covers.
         *
         * @method _setSize
         */
        _setSize: function() {
            var target = this.get('target');
            var width = target.get('offsetWidth');
            var height = target.get('offsetHeight');
            var box = this.get('boundingBox');
            box.set('offsetWidth', width);
            box.set('offsetHeight', height);
        },

        /**
         * Set the position of the indicator, relative to
         * the target it covers.
         *
         * @method _setPosition
         */
        _setPosition: function() {
            var target = this.get('target');
            var xy = target.getXY();
            var box = this.get('boundingBox');
            box.setStyle('position', 'absolute');
            box.setXY(xy);
        },

        /**
         * Build the indicator overlay.
         *
         * @method renderUI
         */
        renderUI: function() {
            var img = Y.Node.create('<img />');
            img.set('src', '/@@/spinner-big');
            this.get('contentBox').append(img);
            this._setSize();
        },

        /**
         * Update the UI according to current state.
         *
         * @method syncUI
         */
        syncUI: function() {
            this._setSize();
            this._setPosition();
        },

        /**
         * Show the overlay indicator
         *
         * let's say we've used it, and it was 'closed', and another event
         * causes us to want to reshow it, you can toggle the disabled which
         * sets a CSS property we can use to show/hide the indicator
         *
         * @method show
         */
        show: function () {
            this.syncUI();
            this.set('disabled', false);
        },

        /**
         * Hide the overlay indicator
         *
         * opposite of show, sets disabled to true and causes the css class to
         * be added back for disabling
         */
        hide: function () {
            this.set('disabled', true);
        }

    });

    var indicator = Y.namespace('lp.indicator');
    indicator.OverlayIndicator = OverlayIndicator;

}, '0.1', {'requires': ['widget']});
