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
        top: 10,
        left: 10,
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
            console.log('setting value', e.newVal);

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
        console.log('setting up clone');

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
        console.log('calling setup clone');

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

        if (scroll_height > this.prev_scroll_height && scroll_height < this.get('max_height')) {
            this.t_area.setStyle('height',
                                 Math.min(scroll_height, this.get('max_height')
            ));
        } else {
            this.t_area.setStyle('height',
                                 Math.max(scroll_height, this.get('min_height')
            ));
        }

        this.set_overflow();
        this.prev_scroll_height = scroll_height;

        // var area = this.t_area,
        //     h = parseInt(area.getStyle('height'), 10),
        //     new_h = 0,
        //     scroll_h = area.get('scrollHeight'),
        //     height_change = scroll_h - this.prev_scroll_height;
        //     line_height = this.get('line_height') || height_change;

        // console.log('use line height', this.use_line_height);
        // console.log(h, new_h, scroll_h, height_change, line_height);

        // if (scroll_h > h) {
        //     console.log('scroll height is bigger');

        //     if (! this.use_line_height) {
        //         if (height_change > 50) {
        //             // Most likely a paste so using the scroll difference would be wrong.
        //             line_height = 0;
        //         } else if (line_height === this.previous_line_height) {
        //             // if the height is the same across multiple calls to
        //             // enlarge area, then this is probably a "typical" line
        //             // height so store it and set that we want to use it as the
        //             // line height going forward for future calls
        //             this.set('line_height', line_height);
        //             this.use_line_height = true;
        //         } else {
        //             this.previous_line_height = line_height;
        //         }
        //     }

        //     new_h = Math.min(scroll_h+line_height, this.get('max_height'));
        //     area.setStyle('height', (new_h+'px'));
        //     this.set_overflow();

        //     this.prev_scroll_height = scroll_h+line_height;
        // } else {
        //     var shrink_by;

        //     console.log('scroll height is smaller');
        //     // we want to shrink things before we set them correctly
        //     // we're going to default and shrink things in a 'guessing' safe
        //     // area
        //     var length_change = prev_val.length - new_val.length;

        //     // if there's more text than before, just return
        //     if (length_change < 0) {
        //         return;
        //     }

        //     if (this.use_line_height) {
        //         shrink_by = this.get('line_height');
        //     } else {
        //         shrink_by = this.ROWS_TO_HEIGHT;
        //     }

        //     console.log(prev_val.length, new_val.length);

        //     // and we need to multiply that line_height value with the number
        //     // of "lines" we think are gone
        //     // a low estimate is 60 characters per line
        //     // so diff new/prev values and mod 60 to get a line count
        //     var line_change = (length_change % 60) * shrink_by;

        //     console.log('shrink', shrink_by);
        //     console.log('shrink', line_change);
        //     area.setStyle('height',
        //             Math.max((scroll_h - line_change), this.MIN_HEIGHT) + "px");

        //     // now update the scroll height since we've adjusted
        //     scroll_h = area.get('scrollHeight');

        //     h = Math.max(this.get('min_height'), scroll_h);
        //     area.setStyle('height', h + "px");
        //     this.set_overflow();
        //     this.prev_scroll_height = h;
        // }
    },

    set_overflow: function() {
        this.t_area.setStyle('overflow',
            (this.t_area.get('scrollHeight') > this.get('max_height') ? "auto" : "hidden"));
    }
});
Y.TextExpander = TextExpander;


}, '@VERSION@' ,{requires:['plugin', 'event-valuechange']});
