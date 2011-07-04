/*
    Copyright (c) 2009, Canonical Ltd.  All rights reserved.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

YUI.add('lazr.effects-async', function(Y) {

/**
 * A quick and simple effect for revealing blocks of text when you click
 * on them.  The first click fetches the content using an AJAX request,
 * after which the widget acts like a regular sliding-reveal.
 *
 * @module lazr.effects
 * @submodule async
 * @namespace lazr.effects
 */

Y.namespace('lazr.effects');

var effects = Y.lazr.effects;
var ui      = Y.lazr.ui;
var FOLDED  = 'lazr-folded';


/**
 * A quick and simple effect for revealing blocks of asynchronously loaded
 * content when you click on them.  The first click fetches the content using
 * an AJAX request, after which the widget acts like a regular sliding-reveal.
 *
 * The function tracks the state of the initial content load by setting the
 * <code>content_loaded</code> attribute on the container object.  The
 * attribute will be set to <code>true</code> after the initial load
 * completes.
 *
 * The trigger recieves the 'lazr-trigger' class, and the content
 * receives 'lazr-content'.
 *
 * Both the trigger and content nodes receive the 'lazr-folded' class whenever
 * the content is closed.
 *
 * The container may also obtain the 'lazr-waiting' and 'lazr-io-error'
 * classes during the asynchronous data fetch.
 *
 * @method async_slideout
 * @public
 * @param slider {Node} The node that will slide open and closed, and hold the
 *  asynchronous content.
 * @param trigger {Node} The node that we will clicked on to open and close
*   the slider.
 * @param uri {String} The URI to fetch the content from.
 * @param container {Node} <i>Optional</i> A child of the sliding
 *  container node that will hold the asynchronous content.
 */
Y.lazr.effects.async_slideout = function(slider, trigger, uri, container) {
    // The slider is busted in IE 7 :(
    if (Y.UA.ie) {
        return;
    }

    // Prepare our object state.
    slider = Y.one(slider);
    if (typeof slider.content_loaded == 'undefined') {
        slider.content_loaded = false;
    }

    if (typeof container == 'undefined' || container === null) {
        // The user didn't give us an explict target container for the new
        // content, so we'll reuse the sliding container node.
        container = slider;
    }

    trigger.addClass(FOLDED);
    trigger.addClass('lazr-trigger');
    slider.addClass(FOLDED);
    slider.addClass('lazr-content');

    trigger.on('click', function(e) {
        e.halt();

        trigger.toggleClass(FOLDED);
        container.toggleClass(FOLDED);

        if (!container.content_loaded) {
            fetch_and_reveal_content(slider, container, uri);
            container.content_loaded = true;
        } else {
            animate_drawer(slider);
        }
    });
};

/*
 * Slide the content in or out by reversing the slider.fx animation object.
 */
function animate_drawer(slider) {
    slider.fx.stop();
    slider.fx.set('reverse', !slider.fx.get("reverse"));
    slider.fx.run();
}

/*
 * Fetch the slide-out drawer's data asynchronously, unset the waiting state,
 * and fill the container with either the new content or an appropriate error
 * message.  Finally, slide the drawer to fit its new contents.
 */
function fetch_and_reveal_content(slider, container, uri) {

    var cfg = {
        on: {
            complete: function() {
                ui.clear_waiting(container);
            },
            success: function(id, response) {
                container.set('innerHTML', response.responseText);
                slider.fx.stop();
                slider.fx = effects.slide_out(slider);
                slider.fx.run();
            },
            failure: function(id, response, args) {
                // Undo the slide animation's changes to the container style.
                slider.setStyles({
                    height:   'auto',
                    overflow: 'visible'
                });
                show_nice_error(id, response, args, container, run_io);
                Y.lazr.anim.red_flash({ node: slider }).run();

                // If the user clicks the collapse trigger, we want to slide
                // the drawer back in.  But doing so first reverses the
                // animation, then runs it (because it assumes that slider.fx
                // is a effects.slide_out() object), so we need to reverse
                // our effects.slide_in() animation, so its state is the same
                // as if it were an open effects.slide_out().
                slider.fx.stop();
                slider.fx = effects.slide_in(slider);
                slider.fx.set('reverse', !slider.fx.get('reverse'));
            }
        }
    };

    // Wrap this in a closure, so we can retry it if there is an error.
    function run_io() {
        ui.waiting(container);
        container.set('innerHTML', '');
        // Slide out enough to fully show the spinner.
        slider.fx = effects.slide_out(slider, { to: { height: '20px' } });
        slider.fx.run();

        Y.io(uri, cfg);
    }
    run_io();
}

/*
 * Display a nice error message in the specified container if the asynchronous
 * data request failed.
 *
 * XXX mars 2009-04-21 bug=364612
 *
 * Need to move this to lazr.io.
 */
function show_nice_error(id, response, args, message_container,
    retry_callback) {
    var status_msg = '<span class="io-status">' +
        response.status + ' ' +
        response.statusText +
        '</span>';
    var msg_html =
        ['<div class="lazr-io-error">',
         '<p>Communication with the server failed</p>',
         '<p>The server\'s response was: ' + status_msg + '</p>',
         '<button title="Try to contact the server again">Retry</button>',
         '</div>'].join('');

    message_container.set('innerHTML', msg_html);

    // Hook up our Retry function.
    message_container.one('button').on('click', function(e) {
        e.halt();
        retry_callback();
    });
}


}, null, { "requires":["node", "event", "io-base", "lazr.base", "lazr.effects",
                       "lazr.anim"]});
