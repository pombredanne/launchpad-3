YUI.add('gallery-text-expander', function(Y) {

var TextExpander = function(cfg) {
    TextExpander.superclass.constructor.apply(this, arguments);
};

TextExpander.NAME = "textExpander";
TextExpander.NS = "expander";

/**
 * ATTRS you can set on initialization to determine how we size the textarea
 *
 */
TextExpander.ATTRS = {
    min_height: {value: null},
    max_height: {value: null}
};

Y.extend(TextExpander, Y.Plugin.Base, {

    // special css we add to clones to make sure they're hidden from view
    CLONE_CSS: {
        position: 'absolute',
        top: -9999,
        left: -9999,
        opacity: 0,
        overflow: 'hidden',
        resize: 'none'
    },

    // defaults for sizing settings in case they're not supplied
    MIN_HEIGHT: 10,
    MAX_HEIGHT: 450,

    prev_scroll_height: 0,

    /**
     * If not default height specified, check for html based default height
     *
     * If there's no default passed into the config and no html based default,
     * use our own constants for it
     *
     */
    _set_start_height: function () {
        if (! this.get('min_height')) {
            this.set('min_height',
                     parseInt(this.t_area.getStyle('height'),
                     this.MIN_HEIGHT));
        }

        if (! this.get('max_height')) {
            this.set('max_height', this.MAX_HEIGHT);
        }
    },

    _bind_events: function () {
        // look at adjusting the size on any value change event including
        // pasting and such
        this.t_area.on('valueChange', function(e) {
            // we need to update the clone with the content so it resizes
            this.clone.set('text', e.newVal);
            this.enlarge_area(e.newVal, e.prevVal);
        }, this);
    },

    /**
     * Given a node, setup a clone so that we can use it for sizing
     *
     * We need to copy this, move it way off the screen and setup some css we
     * use to make sure that we match the original as best as possible.
     *
     * This clone is then checked for the size to use
     *
     */
    _setup_clone: function (node) {
        var clone = node.cloneNode(true);

        clone.setStyles(this.CLONE_CSS);
        clone.removeAttribute('id');
        clone.removeAttribute('name');
        clone.setAttrs('tabIndex', -1);
        clone.set('height', 'auto');
        clone.set('id', 'TESTID');
        Y.one('body').append(clone);

        return clone;
    },

    /**
     * We need to apply some special css to our target we want to resize
     *
     */
    _setup_css: function (target) {
        // don't let this text area be resized in webkit, it'll mess with our
        // calcs and we'll be fighting the whole time for the right size
        target.setStyle('resize', 'none');
        target.setStyle('overflow', 'hidden');

        // we want to add some animation to our adjusting of the size, using
        // css animation to smooth all height changes
        target.setStyle('transition', 'height 0.3s ease');
        target.setStyle('-webkit-transition', 'height 0.3s ease');
        target.setStyle('-moz-transition', 'height 0.3s ease');
    },

    initializer : function(cfg) {
        this.t_area = this.get("host");
        this._setup_css(this.t_area);

        // we need to setup the clone of this node so we can check how big it
        // is, but way off the screen so you don't see it
        this.clone = this._setup_clone(this.t_area);

        this._set_start_height();
        this._bind_events();

        // initial sizing in case there's existing content to match to
        this.enlarge_area();
    },

    enlarge_area: function() {
        // start out just making the hieght the same as the clone's scroll
        // height
        var scroll_height = this.clone.get('scrollHeight');

        if (scroll_height > this.prev_scroll_height) {
            this.t_area.setStyle('height',
                                 Math.min(scroll_height, this.get('max_height')
            ));
        } else if (scroll_height > this.get('max_height')) {
            // a corner case, when we have a lot of text, and we delete some,
            // the scroll height decreases, signalling we should shrink the
            // box, but since we're still larger than the max set...ignore the
            // rule and don't change a thing
        } else {
            this.t_area.setStyle('height',
                                 Math.max(scroll_height, this.get('min_height')
            ));
        }

        // check if the changes above require us to change our overflow setting
        // to allow for a scrollbar now that our max size has been reached
        this.set_overflow();

        this.prev_scroll_height = scroll_height;
    },

    /**
     * Check if we're larger than the max_height setting and enable scrollbar
     *
     */
    set_overflow: function() {
        this.t_area.setStyle('overflow',
            (this.clone.get('scrollHeight') >= this.get('max_height') ? "auto" : "hidden"));
    }
});
Y.TextExpander = TextExpander;


}, '@VERSION@' ,{requires:['plugin', 'event-valuechange']});
