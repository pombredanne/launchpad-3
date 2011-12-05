/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Auto Resizing Textarea Widget.
 *
 * Usage:
 *     Y.one('#myid').plug(ResizingTextarea);
 *     Y.one('#settings').plug(ResizingTextarea, {
 *         min_height: 100
 *     });
 *
 *     Y.all('textarea').plug(ResizingTextarea);
 *
 * @module lp.app.formwidgets
 * @submodule resizing_textarea
 */
YUI.add('lp.app.formwidgets.resizing_textarea', function(Y) {

// Helper: convert size specification like "120px" to a number (in casu, 120).
var strip_px = /px$/;
function parse_size(size) {
    return parseInt(size.replace(strip_px, ''), 10);
}

var module = Y.namespace("lp.app.formwidgets"),
    ResizingTextarea = function(cfg) {
        ResizingTextarea.superclass.constructor.apply(this, arguments);
    };

ResizingTextarea.NAME = "resizing_textarea";
ResizingTextarea.NS = "resizing_textarea";

/**
 * ATTRS you can set on initialization to determine how we size the textarea
 */
ResizingTextarea.ATTRS = {
    /**
     * Get the current elements height. This is READ ONLY
     *
     * @property height
     */
    height: {
        getter: function () {
            return this.t_area.getStyle('height');
        }
    },

    /**
     * Min height to allow the textarea to shrink to in px
     *
     * We check if there's a css rule for existing height and make that the
     * min height in case it's there
     *
     * @property min_height
     */
    min_height: {
        value: 10,

        valueFn: function () {
            var target = this.get("host");
            var css_height = target.getStyle('height');

            return !Y.Lang.isUndefined(css_height) ?
                this._clean_size(css_height) : undefined;
        }
    },

    /**
     * Max height to allow the textarea to grow to in px
     *
     * @property max_height
     */
    max_height: {
        value: 450
    },

    /**
     * Should we bypass animating changes in height
     * Mainly used to turn off for testing to prevent needing to set timeouts
     *
     * @property skip_animations
     */
    skip_animations: {value: false}
};

Y.extend(ResizingTextarea, Y.Plugin.Base, {

    // special css we add to clones to make sure they're hidden from view
    CLONE_CSS: {
        position: 'absolute',
        height: 'auto',
        top: '500px',
        left: 0,
        opacity: 50,
        overflow: 'hidden',
        resize: 'none'
    },

    /**
     * Helper function to turn the string from getComputedStyle to int
     *
     * Deals with the case where we pass in a value with a px at the end. For
     * instance, if you pass the max size from a computed style call, it'll
     * have xxpx which we want to just skip off
     */
    _clean_size: function (val) {
        if (Y.Lang.isString(val) && val.indexOf("px") === -1) {
            val.replace('px', '');
        }
        return parseInt(val, 10);
    },

    // used to track if we're growing/shrinking for each event fired
    _prev_scroll_height: 0,

    /**
     * This is the entry point for the event of change
     *
     * Here we update the clone and resize based on the update
     */
    _run_change: function (new_value) {
        // we need to update the clone with the content so it resizes
        this.clone.set('text', new_value);
        this.resize();
    },

    /**
     * Given a node, setup a clone so that we can use it for sizing
     *
     * We need to copy this, move it way off the screen and setup some css we
     * use to make sure that we match the original as best as possible.
     *
     * This clone is then checked for the size to use
     */
    _setup_clone: function (node) {
        this.clone = node.cloneNode(true);

        this.clone.setStyles(this.CLONE_CSS);
        // remove attributes so we don't accidentally grab this node in the
        // future
        this.clone.removeAttribute('id');
        this.clone.removeAttribute('name');
        this.clone.generateID();
        this.clone.setAttrs({
            'tabIndex': -1
        });

        this._update_clone_width();

        node.get('parentNode').append(this.clone);
        return this.clone;
    },

    /**
     * We need to apply some special css to our target we want to resize
     */
    _setup_css: function () {
        // don't let this text area be resized in the browser, it'll mess with
        // our calcs and we'll be fighting the whole time for the right size
        this.t_area.setStyle('resize', 'none');
        this.t_area.setStyle('overflow', 'hidden');

        // we want to add some animation to our adjusting of the size, using
        // css animation to smooth all height changes
        if (!this.get('skip_animations')) {
            this.t_area.setStyle('transition', 'height 0.3s ease');
            this.t_area.setStyle('-webkit-transition', 'height 0.3s ease');
            this.t_area.setStyle('-moz-transition', 'height 0.3s ease');
        }
    },

    /**
     * update the css width of the clone node
     *
     * In the process of page dom manipulation, the width might change based
     * on other nodes showing up and forcing changes due to padding/etc.
     *
     * We'll play safe and just always recalc the width for the clone before
     * we check it's scroll height
     *
     */
    _update_clone_width: function () {
        this.clone.setStyle('width', this.t_area.getComputedStyle('width'));
    },

    initializer : function(cfg) {
        var that = this;
        this.t_area = this.get("host");

        // we need to clean the px of any defaults passed in
        this.set('min_height', this._clean_size(this.get('min_height')));
        this.set('max_height', this._clean_size(this.get('max_height')));

        this._setup_css(this.t_area);

        // we need to setup the clone of this node so we can check how big it
        // is, but way off the screen so you don't see it
        this._setup_clone(this.t_area);

        // look at adjusting the size on any value change event including
        // pasting and such
        this.t_area.on('valueChange', function(e) {
            this._run_change(e.newVal);
        }, this);

        // we also want to handle adjusting if the user resizes their browser
        Y.on('windowresize', function(e) {
            that._run_change(that.t_area.get('value'));
        }, this);

        // initial sizing in case there's existing content to match to
        this.resize();
    },

    /**
     * Adjust the size of the textarea as needed
     *
     * @method resize
     */
    resize: function() {
        // we need to update the clone width in case the node's width has
        // changed
        this._update_clone_width();

        var scroll_height = this.clone.get('scrollHeight');

        // only update the height if we've changed
        if (this._prev_scroll_height !== scroll_height) {
            new_height = Math.max(
                this.get('min_height'),
                Math.min(scroll_height, this.get('max_height')));

            this.t_area.setStyle('height', new_height);

            // check if the changes above require us to change our overflow
            // setting to allow for a scrollbar now that our max size has been
            // reached
            this.set_overflow();

            this._prev_scroll_height = scroll_height;
        }
    },

    /**
     * Check if we're larger than the max_height setting and enable scrollbar
     *
     * @method set_overflow
     */
    set_overflow: function() {
        var overflow = "hidden";

        if (this.clone.get('scrollHeight') >= this.get('max_height')) {
            overflow = "auto";
        }
        this.t_area.setStyle('overflow', overflow);
    }
});

// add onto the formwidget namespace
module.ResizingTextarea = ResizingTextarea;

}, "0.1", {
    "requires": ["plugin", "node", "event-valuechange", "event-resize"]
});
