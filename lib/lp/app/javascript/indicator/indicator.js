/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Client-side rendering of bug listings.
 *
 * @module lp.indicator
 *
 * Usage:
 *     adds a .indicator on the target node for api controls
 *     Y.one('#id').plug(lp.indicator.IndicatorPlugin)
 *
 *     or directly without the plugin, but then you have to control the
 *     disabled flags on it yourself for show/hide/etc
 *     lp.indicator.IndicatorWidget({
 *         target: Y.one('#id')
 *     });
 *
 */
YUI().add('lp.indicator', function (Y) {

    // Our spinner is 32px, we use this for calculating the center position of
    // the spinner within the overlay div
    var SPINNER_SIZE = 32;

    var props = {
        ATTRS: {
            /**
             * A reference to the node that we're going to overlay.
             *
             * @attribute target
             * @type Y.Node
             * @default null
             */
            target: {
                value: null
            },

            /**
             * Callback to fire upon calling success.
             *
             * @attribute success_action
             * @type Function
             * @default null
             */
            success_action: {
                value: null
            },

            /**
             * Callback to fire upon calling error.
             *
             * @attribute error_action
             * @type Function
             * @default null
             */
            error_action: {
                value: null
            }
        }
    };

    var config = {

        /**
         * Calc the padding we need to use to center the spinner
         */
        _calc_image_padding: function (dim) {
            var boundingBox = this.get('boundingBox');
            var content_height =
                boundingBox.getStyle(dim).replace('px', '');
            return content_height > SPINNER_SIZE ?
                (content_height - SPINNER_SIZE) / 2.0 : 0;
        },

        /**
         * YUI init
         *
         * @method initializer
         */
        initializer: function(cfg) {
            this.hide();
        },

        _addListeners: function() {
            this.on('visibleChange', function(e) {
                if (e.newVal === true) {
                    this.resizeAndReposition();
                }
            }, this);
        },

        /**
         * To prevent having to force call sites to pass in
         * parentNode, we must overridge YUI's built-in _renderUI
         * method.
         *
         * This is a copy of the YUI method, except for using our
         * own parentNode.  This is needed so the spinner overlays
         * correctly.
         *
         * @method _renderUI
         */
         _renderUI: function() {
             var local_parent = this.get('target').get('parentNode');
             this._renderBoxClassNames();
             this._renderBox(local_parent);
         },

        /**
         * Build the indicator overlay itself
         *
         * @method renderUI
         */
        renderUI: function () {
            var node_html = '<img/>';
            var img = Y.Node.create(node_html);
            img.set('src', '/@@/spinner-big');
            this.get('contentBox').append(img);
        },

        bindUI: function() {
            this._addListeners();
        },

        // Whenever the target changes it's position, we resize catching the
        // event from the Y.Widget.Position extension.
        resizeAndReposition: function () {
            var boundingBox = this.get('boundingBox');
            var target = this.get('target');
            var width = target.get('offsetWidth');
            var height = target.get('offsetHeight');
            boundingBox.set('offsetWidth', width);
            boundingBox.set('offsetHeight', height);
            // Now do position too.
            boundingBox.setXY(target.getXY());
            // update the padding on the image to fit
            var img = boundingBox.one('img');
            img.setStyle('top', this._calc_image_padding('height') + 'px');
            img.setStyle('left', this._calc_image_padding('width') + 'px');
        },

        /**
         * Mark the loading or busy action as in progress,
         * and show the overlay.
         *
         * @method setBusy
         */
        setBusy: function() {
            this.show();
        },

        success: function() {
            this.hide();
            var callback = this.get('success_action');
            if (Y.Lang.isFunction(callback)) {
                callback.call(this);
            }
        },

        error: function() {
            this.hide();
            var callback = this.get('error_action');
            if (Y.Lang.isFunction(callback)) {
                callback.call(this);
            }
        }
    };


    /**
     * This is using the YUI concept of class extensions to get us min-in like
     * features from the Widget classes. This keeps us from having to do a
     * bunch of position work ourselves.
     */
    var OverlayIndicator = Y.Base.create(
            'overlay-indicator',
            Y.Widget,
            [],
            config,
            props
    );

    /**
     * Actions are pre-built responses that can be used as success and
     * error actions
     *
     * All actions are called within the scope of the widget created and
     * assigned to.
     *
     */
    var actions = {
        /**
         * Scroll to the top left point of the target node we're working off
         * of.
         *
         * We're only going to change focus if the target's XY position
         * isn't in the current viewport.
         */
        scroll_to_target: function () {
           var target = this.get('target').getXY();
           var viewport = Y.DOM.viewportRegion();
           // Do we want to do the scroll move?
           var scroll = false;
           // If our target X is too far left or right for us to see, scroll
           // our viewport.
           if (target[0] < viewport.left || target[0] > viewport.right) {
               scroll = true;
           }
           // Verify if our Y is out of viewport scope.
           if (target[1] < viewport.top || target[1] > viewport.bottom) {
               scroll = true;
           }
           if (scroll) {
               window.scrollTo(target[0], target[1]);
           }
        }
    };

    var indicator = Y.namespace('lp.indicator');
    indicator.OverlayIndicator = OverlayIndicator;
    indicator.actions = actions;

}, '0.1', {requires: ['base', 'widget']});
