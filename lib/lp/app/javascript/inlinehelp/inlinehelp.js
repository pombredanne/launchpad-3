/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @module lp.app.inlinehelp
 */
YUI.add('lp.app.inlinehelp', function (Y) {

    var module = Y.namespace('lp.app.inlinehelp');
    var HELP_LINK_SELECTOR = 'a[target=help]';
    var HELP_CSS = 'help';
    var CLICK_DELEGATE = false;

    /**
     * Handle the clicking of a help link in the body
     * This is a delegated handler so this == the object clicked
     */
    module._show_help = function (e) {
        e.preventDefault();
        var target_link = e.currentTarget;

        // init the overlay and show it
        var overlay = new module.InlineHelpOverlay({
            'contentUrl': target_link.get('href'),
            'align': {
                points:[Y.WidgetPositionAlign.TL, Y.WidgetPositionAlign.TL]
            },
            'constrain': true
        });
        overlay.render();
    };

    module.init_help =  function () {
        // find the help links
        var links = Y.all(HELP_LINK_SELECTOR);

        // add the help class
        links.addClass(HELP_CSS);

        // bind the click events but unbind it first in case we're re-running
        // init more than once (say on ajax loading of new help content)
        var body = Y.one('body');
        if (CLICK_DELEGATE !== false) {
            CLICK_DELEGATE.detach();
        }
        CLICK_DELEGATE = body.delegate(
            'click',
            module._show_help,
            HELP_LINK_SELECTOR
        );
    };

    module.InlineHelpOverlay = Y.Base.create(
        'inlinehelp-overlay',
        Y.lazr.PrettyOverlay,
        [],
        {
            _get_content_cfg: {
                method: "GET",
                on: {
                    success: function (id, o, args) {
                        var data = o.responseText; // Response data.
                        this.set('bodyContent', data);
                    },
                    failure: function (id, o, args) {
                        Y.log('failed to fetch content for InlineHelpOverlay');
                        this.set('bodyContent', 'Failed to fetch help content');
                    }
                }
            },

            _getContent: function () {
                var cfg = this._get_content_cfg;
                // we want the context in the ajax event handlers to be this
                // instance of the object
                cfg.context = this;
                var request = Y.io(this.get('contentUrl'), cfg);
            },

            initializer: function (cfg) {
                // we need to deal with our remote content for the bodyContent
                this._getContent();
            },

            /*
             * Override widget's hide/show methods, since DiffOverlay
             * doesn't provide CSS to handle .visible objects.
             */
            hide: function() {
                this.constructor.superclass.hide.call(this);
                this.get('boundingBox').setStyle('display', 'none');
            },

            show: function() {
                this.constructor.superclass.show.call(this);
                this.get('boundingBox').setStyle('display', 'block');
            }
        },
        {
            ATTRS: {
                contentUrl: {
                    value: ''
                },
                progressbar: {
                    value: false
                },
            }
        }
    );

}, "0.1", { "requires": ['lazr.overlay', 'io', 'log',] });
