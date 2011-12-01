/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI().add('lp.indicator', function (Y) {

    // our spinneris 32px, we use this for calculating the center position of
    // the spinner within the overlay div
    var SPINNER_SIZE = 32;

    /**
     * An Overlay overlay-style loading indicator widget
     *
     * It's using the Y.Widget components to handle keeping in sync with the
     * UI of the "constrain". It keeps our x/y fixed, we only have to manage
     * the height/width of our box we're overlaying.
     *
     * Right now we try to center the spinner image over the target.
     *
     * @module lp.indicator
     */
    function IndicatorWidget() {
        IndicatorWidget.superclass.constructor.apply(this, arguments);
    }

    IndicatorWidget.NAME = 'indicator-widget';
    IndicatorWidget.ATTRS = {};

    Y.extend(IndicatorWidget, Y.Widget, {


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
        initializer: function () {
            this.on('constrain|xyChange', this.resize);
        },

        /**
         * Build the indicator overlay itself
         *
         * @method renderUI
         */
        renderUI: function () {
            var node_html = ['<img style="max-width: 100%; ',
                             'display: block; margin: auto;"/>'].join("");
            var img = Y.Node.create(node_html);
            img.set('src', '/@@/spinner-big');
            this.get('contentBox').append(img);
        },

        // whenever the target changes it's position, we resize catching the
        // event from the Y.Widget.Position extension
        resize: function () {
            var boundingBox = this.get('boundingBox');
            var target = this.get('constrain');

            boundingBox.setStyles({
                width: target.getStyle('width'),
                height: target.getStyle('height')
            });

            // update the padding on the image to fit
            var img = boundingBox.one('img');
            img.setStyle('top', this._calc_image_padding('height') + 'px');
            img.setStyle('left', this._calc_image_padding('width') + 'px');
        }
    });

    /**
     * This is using the YUI concept of class extensions to get us min-in like
     * features from the Widget classes. This keeps us from having to do a
     * bunch of position work ourselves.
     */
    var OverlayIndicator = Y.Base.build(
            "overlayIndicator",
            IndicatorWidget,
            [Y.WidgetPosition, Y.WidgetPositionAlign,
                Y.WidgetPositionConstrain]
        );

    /**
     * An indicator plugin we can stick on a node, this creates the instance
     * of the overlay indicator and we could create other types down the road
     */
    function IndicatorPlugin(config) {
        IndicatorPlugin.superclass.constructor.apply(this, arguments);
    }

    // Once we plug it into the target, we can access it via target.indicator.
    // This has it's own api for show() and hide() which toggle the widgets
    // disabled property and thus css from YUI.
    IndicatorPlugin.NS = "indicator";
    IndicatorPlugin.NAME = "indicatorPlugin";

    IndicatorPlugin.ATTRS = {
        /**
         * By default the indicator isn't visible, use .show for that
         *
         * @attribute visible
         * @type boolean
         * @default false
         */
        visible: {
            value: false
        }
    };

    Y.extend(IndicatorPlugin, Y.Plugin.Base, {

        // we're showing and hiding based on the disabled property of the YUI
        // widget we've created. Visible to the plugin == disabled on the
        // widget instance
        _changeVisible: function (e) {
            var is_visible = e.newVal;
            this._instance.set('disabled', !is_visible);
        },

        _setup_overlay: function () {
            var host = this.get('host');

            this._instance = new OverlayIndicator({
                constrain: host,
                disabled: !this.get('visible'),
                preventOverlap: true
            });

            // render out to the parent node of the target
            this._instance.render(host.get('parentNode'));
        },

        initializer: function (cfg) {
            this._setup_overlay();

            // listen for changes to the visible property, if that changes we
            // want to toggle the disabled on our indicator instance
            this.after('visibleChange', this._changeVisible);
        },

        /**
         * show the indicator widget
         *
         * @method show
         */
        show: function () {
            // before we show, make sure our size is right
            this.resize();
            this.set('visible', true);
        },

        /**
         * Hide the indicator widget
         *
         * @method hide
         */
        hide: function () {
            this.set('visible', false);
        },

        /**
         * Manually force a resize calc of the overlay widget
         */
        resize: function () {
            this._instance.resize();
        }
    });

    var indicator = Y.namespace('lp.indicator');
    indicator.IndicatorPlugin = IndicatorPlugin;
    indicator.OverlayIndicator = OverlayIndicator;

}, '0.1', { requires:
    [ 'widget', 'plugin', 'widget-position', 'widget-position-constrain',
        'widget-position-align']
});
