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
    module.show_help = function (e) {
        e.preventDefault();
        console.log('in orig show help');
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
            module.show_help,
            HELP_LINK_SELECTOR
        );
    };

    // module.InlineHelpOverlay = Y.Base.create(
    //     'inlinehelp-overlay',
    //     Y.lazr.PrettyOverlay,
    //     [],
    //     {
    //         bindUI: function () {
    //             // call the parent bindUI method first
    //             this.superclass.bindUI.apply(this, arguments);
    //         },

    //     },
    //     {
    //         ATTRS: {
    //             progressbar: {
    //                 value: false
    //             },
    //         }
    //     }
    // );

}, "0.1", { "requires": ["lazr.overlay"] });
