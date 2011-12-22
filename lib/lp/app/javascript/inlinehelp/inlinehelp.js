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

    /**
     * Handle the clicking of a help link in the body
     * This is a delegated handler so this == the object clicked
     *
     * 
     */
    module.show_help = function (e) {

    };

    module.init_help =  function () {
        // find the help links
        var links = Y.all(HELP_LINK_SELECTOR);

        // add the help class
        links.addClass(HELP_CSS);

        // bind the click events
        Y.one('body').delegate('click', module.show_help, HELP_LINK_SELECTOR);
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
