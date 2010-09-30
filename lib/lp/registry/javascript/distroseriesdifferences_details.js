/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Enhancements for the distroseries differences page.
 *
 * @module registry
 * @submodule distroseriesdifferences_details
 * @requires  io-base, lp.soyuz.base
 */
YUI.add('lp.registry.distroseriesdifferences_details', function(Y) {

var namespace = Y.namespace('lp.registry.distroseriesdifferences_details');

/**
 * Create one Launchpad client that will be used with multiple requests.
 */
var lp_client = new LP.client.Launchpad();

/*
 * Setup the expandable rows for each difference.
 *
 * @method setup_expandable_rows
 */
namespace.setup_expandable_rows = function() {

    var blacklist_handler = function(e, api_uri, source_name) {
        // We only want to select the new radio if the update is
        // successful.
        e.preventDefault();
        var blacklist_options_container = this.ancestor('div');

        // Disable all the inputs
        blacklist_options_container.all('input').set('disabled', 'disabled');
        e.target.prepend('<img src="/@@/spinner" />');

        var method_name = (e.target.get('value') == 'NONE') ?
            'unblacklist' : 'blacklist';
        var blacklist_all = (e.target.get('value') == 'BLACKLISTED_ALWAYS');

        var diff_rows = Y.all('tr.' + source_name);

        var config = {
            on: {
                success: function(updated_entry, args) {
                    // Let the user know this item is now blacklisted.
                    blacklist_options_container.one('img').remove();
                    blacklist_options_container.all(
                        'input').set('disabled', false);
                    e.target.set('checked', true);
                    Y.each(diff_rows, function(diff_row) {
                        var fade_to_gray = new Y.Anim({
                            node: diff_row,
                            from: { backgroundColor: '#FFFFFF'},
                            to: { backgroundColor: '#EEEEEE'}
                            });
                        if (method_name == 'unblacklist') {
                            fade_to_gray.set('reverse', true);
                            }
                        fade_to_gray.run();
                        });
                },
                failure: function(id, response) {
                    blacklist_options_container.one('img').remove();
                    blacklist_options_container.all(
                        'input').set('disabled', false);
                }
            },
            parameters: {
                all: blacklist_all
            }
        };

        lp_client.named_post(api_uri, method_name, config);

    };

    /**
     * Link the click event for these blacklist options to the correct
     * api uri.
     *
     * @param blacklist_options {Node} The node containing the blacklist
     *                          options.
     * @param source_name {string} The name of the source to update.
     */
    var setup_blacklist_options = function(
        blacklist_options, source_name, api_uri) {
        Y.on('click', blacklist_handler, blacklist_options.all('input'),
             blacklist_options, api_uri, source_name);
    };

    var add_comment_handler = function(placeholder, api_uri) {
        placeholder.all('textarea,button').set('disabled', 'disabled');
        placeholder.one('div.widget-bd').append('<img src="/@@/spinner" />');

        var comment_text = placeholder.one('textarea').get('value');

        var success_handler = function(comment_entry) {
            // Grab the XHTML representation of the comment
            // and prepend it to the list of comments.
            config = {
                on: {
                    success: function(comment_html) {
                        //add_comment_html(comment_html);
                        debugger;
                    }
                    },
                accept: LP.client.XHTML
                };
            lp_client.get(comment_entry.get('self_link'), config);

        };
        var failure_handler = function(id, response) {
            debugger;
        };

        var config = {
            on: {
                success: success_handler,
                failure: failure_handler
                },
            parameters: {
                comment: comment_text
                }
            };
        lp_client.named_post(api_uri, 'addComment', config);
    };

    var setup_add_comment = function(placeholder, api_uri) {
        placeholder.insert([
            '<a class="widget-hd js-action sprite add" href="#">',
            '  Add comment</a>',
            '<div class="widget-bd lazr-closed" ',
            '     style="height:0;overflow:hidden">',
            '  <textarea></textarea><button>Save comment</button>',
            '</div>'
            ].join(''), 'replace');

        // The comment area should slide in when the 'Add comment'
        // action is clicked.
        var slide;
        placeholder.one('a.widget-hd').on('click', function(e) {
            e.preventDefault();
            if (!slide) {
                slide = Y.lazr.effects.slide_out(
                    placeholder.one('div.widget-bd'));
            } else {
                slide.set('reverse', !slide.get('reverse'));
            }
            slide.stop();
            slide.run();
        });

        placeholder.one('button').on('click', function(e) {
            add_comment_handler(placeholder, api_uri);
        });
    };

    /**
     * Get the extra information for this diff to display.
     *
     * @param uri {string} The uri for the extra diff info.
     * @param container {Node} A node which must contain a div with the
     *                  class 'diff-extra-container' into which the results
     *                  are inserted.
     */
    var get_extra_diff_info = function(uri, container, source_name) {

        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            'Fetching difference details ...')
        container.one('div.diff-extra-container').insert(
            in_progress_message, 'replace');

        var success_cb = function(transaction_id, response, args) {
            args.container.one('div.diff-extra-container').insert(
                response.responseText, 'replace');
            var api_uri = [
                LP.client.cache.context.self_link,
                '+difference',
                source_name
                ].join('/')
            setup_blacklist_options(args.container.one(
                'div.blacklist-options'), source_name, api_uri);
            setup_add_comment(args.container.one(
                'div.add-comment-placeholder'), api_uri);
            };

        var failure_cb = function(transaction_id, response, args){
           var retry_handler = function(e) {
               e.preventDefault();
               get_extra_diff_info(args.uri, args.container);
               };
           var failure_message = Y.lp.soyuz.base.makeFailureNode(
               'Failed to fetch difference details.',
               retry_handler);
           args.container.insert(failure_message, 'replace');

           var anim = Y.lazr.anim.red_flash({
                node: args.container
                });
           anim.run();
           };

        var config = {
            on: {
                'success': success_cb,
                'failure': failure_cb,
            },
            arguments: {
                'container': container,
                'uri': uri
            }
        };
        Y.io(uri, config);

    };

    var expander_handler = function(e) {
        e.preventDefault();
        var toggle = e.currentTarget;
        var row = toggle.ancestor('tr');
        toggle.toggleClass('treeCollapsed').toggleClass('treeExpanded');

        // Only insert if there isn't already a container row there.
        next_row = row.next();
        if (next_row == null || !next_row.hasClass('diff-extra')) {
            var source_name = row.one('a.toggle-extra').get('text');
            var details_row = Y.Node.create([
                '<table><tr class="diff-extra unseen ' + source_name + '">',
                '  <td colspan="5">',
                '    <div class="diff-extra-container"></div>',
                '  </td></tr></table>'
                ].join('')).one('tr');
            row.insert(details_row, 'after');
            var uri = toggle.get('href');
            get_extra_diff_info(uri, details_row.one('td'), source_name);
        } else {
            details_row = next_row
        }
        details_row.toggleClass('unseen');
    };

    Y.all('table.listing a.toggle-extra').each(function(toggle){
        toggle.addClass('treeCollapsed').addClass('sprite');
        toggle.on("click", expander_handler);
    })

};

}, "0.1", {"requires": [
    "io-base", "lp.soyuz.base", "lazr.anim", "lazr.effects"]});
