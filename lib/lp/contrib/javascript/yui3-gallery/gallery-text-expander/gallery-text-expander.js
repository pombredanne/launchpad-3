YUI.add('gallery-text-expander', function(Y) {

var TextExpander = function(cfg) {
    TextExpander.superclass.constructor.apply(this, arguments);
};

TextExpander.NAME = "textExpander";
TextExpander.NS = "expander";

TextExpander.ATTRS = {
    line_height: {
        value: null,
    },
    min_height: {value: null},
    max_height: {value: null}
};

Y.extend(TextExpander, Y.Plugin.Base, {

    MIN_HEIGHT: 10,
    MAX_HEIGHT: 450,
    ROWS_TO_HEIGHT: 35,

    prev_scroll_height: null,
    previous_line_height: null,
    use_line_height: false,

    /**
     * Determine what the default sizes are for this textarea
     *
     */
    _determine_line_height: function () {
        this.prev_scroll_height = this.t_area.get('scrollHeight');

        // if we have a line height from the init config then it wins!
        if (this.get('line_height')) {
            this.use_line_height = true;
        }

        // else determine what height to use based on current html
        if(!this.get('line_height')) {
            if (this.t_area.get('lineHeight')) {
                this.set('line_height', this.t_area.get('lineHeight'));
                this.use_line_height = true;
            } else if (this.t_area.get('fontSize')) {
                this.set('line_height', this.t_area.get('fontSize'));
                this.use_line_height = true;
            }
        }
    },

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
            if (this.use_line_height) {
                this.set('max_height',
                    this.get('line_height') * this.ROWS_TO_HEIGHT);
            } else {
                this.set('max_height',
                    this.MAX_HEIGHT);
            }
        }
    },

    _bind_events: function () {
        // look at adjusting the size on any value change event including
        // pasting and such
        this.t_area.on('valueChange', function(e) {
            this.enlarge_area(e.newVal, e.prevVal);
        }, this);
    },

    initializer : function(cfg) {
        this.t_area = this.get("host");
        this._determine_line_height();
        this._set_start_height();
        this.t_area.setStyle('overflow', 'hidden');

        this._bind_events();

        // initial sizing in case there's existing content to match to
        this.enlarge_area(this.t_area.get('value').length, 0);
    },

    enlarge_area: function(new_val, prev_val) {
        var area = this.t_area,
            h = parseInt(area.getStyle('height'), 10),
            new_h = 0,
            scroll_h = area.get('scrollHeight'),
            height_change = scroll_h - this.prev_scroll_height;
            line_height = this.get('line_height') || height_change;

        console.log('use line height', this.use_line_height);
        console.log(h, new_h, scroll_h, height_change, line_height);

        if (scroll_h > h) {
            console.log('scroll height is bigger');

            if (! this.use_line_height) {
                if (height_change > 50) {
                    // Most likely a paste so using the scroll difference would be wrong.
                    line_height = 0;
                } else if (line_height === this.previous_line_height) {
                    // if the height is the same across multiple calls to
                    // enlarge area, then this is probably a "typical" line
                    // height so store it and set that we want to use it as the
                    // line height going forward for future calls
                    this.set('line_height', line_height);
                    this.use_line_height = true;
                } else {
                    this.previous_line_height = line_height;
                }
            }

            new_h = Math.min(scroll_h+line_height, this.get('max_height'));
            area.setStyle('height', (new_h+'px'));
            this.set_overflow();

            this.prev_scroll_height = scroll_h+line_height;
        } else {
            console.log('scroll height is smaller');
            // we want to shrink things before we set them correctly
            // we're going to default and shrink things in a 'guessing' safe
            // area
            var length_change = prev_val.length - new_val.length;

            // if there's more text than before, just return
            if (length_change < 0) {
                return;
            }

            if (this.use_line_height) {
                var shrink_by = this.get('line_height');
            } else {
                var shrink_by = this.ROWS_TO_HEIGHT;
            }

            console.log(prev_val.length, new_val.length);

            // and we need to multiply that line_height value with the number
            // of "lines" we think are gone
            // a low estimate is 60 characters per line
            // so diff new/prev values and mod 60 to get a line count
            var line_change = (length_change % 60) * shrink_by;

            console.log('shrink', shrink_by);
            console.log('shrink', line_change);
            area.setStyle('height',
                    Math.max((scroll_h - line_change), this.MIN_HEIGHT) + "px");

            // now update the scroll height since we've adjusted
            scroll_h = area.get('scrollHeight'),

            h = Math.max(this.get('min_height'), scroll_h);
            area.setStyle('height', h + "px");
            this.set_overflow();
            this.prev_scroll_height = h;
        }
    },

    set_overflow: function() {
        this.t_area.setStyle('overflow',
            (this.t_area.get('scrollHeight') > this.get('max_height') ? "auto" : "hidden"));
    }
});
Y.TextExpander = TextExpander;


}, '@VERSION@' ,{requires:['plugin', 'event-valuechange']});
