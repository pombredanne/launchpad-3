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
var lp_client = new Y.lp.client.Launchpad();

/*
 * Setup the expandable rows for each difference.
 *
 * @method setup_expandable_rows
 */
namespace.setup_expandable_rows = function() {

    var blacklist_handler = function(e, dsd_link, source_name) {
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

        lp_client.named_post(dsd_link, method_name, config);

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
        blacklist_options, source_name, dsd_link) {
        Y.on('click', blacklist_handler, blacklist_options.all('input'),
             blacklist_options, dsd_link, source_name);
    };

    /**
     * Toggle the spinner and enable/disable comment fields.
     *
     * @param comment_form {Node} The node that contains the relevant
     *                     comment fields.
     */
    var toggle_comment_in_progress = function(comment_form) {
        var spinner = comment_form.one('img');
        if (Y.Lang.isNull(spinner)) {
            comment_form.one('div.widget-bd').append(
                '<img src="/@@/spinner" />');
            comment_form.all('textarea,button').set(
                'disabled', 'disabled');
        } else {
            comment_form.one('img').remove();
            comment_form.all('textarea,button').set(
                'disabled', '');
        }
    };

    /**
     * Handle the add comment event.
     *
     * This method adds a comment via the API and update the UI.
     *
     * @param comment_form {Node} The node that contains the relevant comment
     *                            fields.
     * @param api_uri {string} The uri for the distroseriesdifference to which
     *                the comment is to be added.
     */
    var add_comment_handler = function(comment_form, api_uri) {

        var comment_text = comment_form.one('textarea').get('value');

        toggle_comment_in_progress(comment_form);

        var success_handler = function(comment_entry) {
            // Grab the XHTML representation of the comment
            // and prepend it to the list of comments.
            config = {
                on: {
                    success: function(comment_html) {
                        comment_node = Y.Node.create(comment_html);
                        comment_form.insert(comment_node, 'before');
                        var anim = Y.lazr.anim.green_flash({
                            node: comment_node
                            });
                        anim.run();
                    }
                    },
                accept: Y.lp.client.XHTML
                };
            lp_client.get(comment_entry.get('self_link'), config);
            comment_form.one('textarea').set('value', '');
            toggle_comment_in_progress(comment_form);
        };
        var failure_handler = function(id, response) {
            // Re-enable field with red flash.
            toggle_comment_in_progress(comment_form);
            var anim = Y.lazr.anim.red_flash({
                node: comment_form
                });
            anim.run();
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

    /**
     * Add the comment fields ready for sliding out.
     *
     * This method adds the markup for a slide-out comment and sets
     * the event handlers.
     *
     * @param placeholder {Node} The node that is to contain the comment
     *                            fields.
     * @param api_uri {string} The uri for the distroseriesdifference to which
     *                the comment is to be added.
     */
    var setup_add_comment = function(placeholder, api_uri) {
        placeholder.insert([
            '<a class="widget-hd js-action sprite add" href="">',
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
            e.preventDefault();
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
            'Fetching difference details ...');
        container.one('div.diff-extra-container').insert(
            in_progress_message, 'replace');
        var success_cb = function(transaction_id, response, args) {
            args.container.one('div.diff-extra-container').insert(
                response.responseText, 'replace');
            var api_uri = [
                LP.cache.context.self_link,
                '+difference',
                source_name
                ].join('/');
            blacklist_slot = args.container.one('div.blacklist-options');
            // The blacklist slot can be null if the user's not allowed
            // to edit this difference.
            if (blacklist_slot !== null) {
                setup_blacklist_options(blacklist_slot, source_name, api_uri);
                setup_add_comment(
                    args.container.one('div.add-comment-placeholder'),
                    api_uri);
                namespace.setup_packages_diff_states(args.container, api_uri);
          }
        };

        var failure_cb = function(transaction_id, response, args) {
            var retry_handler = function(e) {
                e.preventDefault();
                get_extra_diff_info(
                    args.uri, args.container, args.source_name);
            };
            var failure_message = Y.lp.soyuz.base.makeFailureNode(
                Y.Escape.html('Failed to fetch difference details.'),
                retry_handler);
            container.insert(failure_message, 'replace');

            var anim = Y.lazr.anim.red_flash({
                 node: args.container
                 });
            anim.run();
        };

        var config = {
            headers: {'Accept': 'application/json;'},
            on: {
                'success': success_cb,
                'failure': failure_cb,
            },
            arguments: {
                'container': container,
                'uri': uri,
                'source_name': source_name
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


var set_package_diff_status = function(container, new_status, note_msg) {
    container.removeClass('request-derived-diff');
    container.removeClass('PENDING');
    note = container.all('.note').remove();
    container.addClass(new_status);
    if (note_msg !== undefined) {
        container.append([
            '<span class="note greyed-out">(',
            note_msg,
            ')</span>'].join(''));
    }
};

/*
* Helper function to extract the selected state from a jsonified
* Vocabulary.
*
* @param json_voc {object} A jsonified Vocabulary
*
*/
namespace.get_selected = function(json_voc) {
    for (var i = 0; i < json_voc.length; i++) {
        var obj = json_voc[i];
        if (obj.selected === true) {
            return obj;
        }
    }
    return undefined;
};

namespace.add_link_to_package_diff = function(container, url_uri) {
    var y_config = {
        headers: {'Accept': 'application/json;'},
        on: {
            success: function(url) {
                container.all('.update-failure-message').remove();
                container
                    .wrap('<a />')
                    .ancestor()
                        .set("href", url);
            },
            failure: function(url) {
                container.all('.update-failure-message').remove();

                var retry_handler = function(e) {
                    e.preventDefault();
                    namespace.add_link_to_package_diff(container, url_uri);
                };
                var failure_message = Y.lp.soyuz.base.makeFailureNode(
                    Y.Escape.html('Failed to fetch package diff url.'),
                    retry_handler);
                container.insert(failure_message);
            }
        }
    };
    lp_client.named_get(url_uri , null, y_config);
};

/**
* Polling intervall for checking package diff's status.
*/
namespace.poll_interval = 30000;

/**
* Attach package diff status poller.
*
* This method attachs a poller to the container to check
* the package diff object's status.
*
* @param container {Node} The container node displaying this package
* diff information.
*
* @dsd_link {string} The uri for the distroseriesdifference object.
*/
namespace.setup_pending_package_diff = function(container, dsd_link) {
    var parent = container.hasClass('parent');
    var package_diff_uri = [
        dsd_link,
        parent ? 'parent_package_diff_status' : 'package_diff_status',
        ].join('/');
    var build_package_diff_update_config = {
        uri: package_diff_uri,
        lp_client: lp_client,
        parent: parent,
        /**
        * This function knows how to update a package diff status.
        *
        * @config domUpdateFunction
        */
        domUpdateFunction: function(container, data_object) {
            var state_and_name = namespace.get_selected(data_object);
            var state = state_and_name.token;
            var name = state_and_name.title;
            if (state === 'FAILED') {
                set_package_diff_status(container, 'FAILED', name);
                var anim = Y.lazr.anim.red_flash({
                    node: container
                });
                anim.run();
             }
            else if (state === 'COMPLETED') {
                set_package_diff_status(container, 'COMPLETED');
                url_uri = [
                    dsd_link,
                    parent ? 'parent_package_diff_url' : 'package_diff_url'
                    ].join('/');
                namespace.add_link_to_package_diff(container, url_uri);
                var anim = Y.lazr.anim.green_flash({
                    node: container
                });
                anim.run();
             }
        },

        interval: namespace.poll_interval,

        /**
        * This function knows whether the package diff status
        * should stop being updated. It checks whether the state
        * is COMPLETED or FAILED.
        *
        * @config stopUpdatesCheckFunction
        */
        stopUpdatesCheckFunction: function(container){
            if (container.hasClass("COMPLETED")) {
                return true;
            }
            else if (container.hasClass("FAILED")) {
                return true;
            }
            else {
                return false;
            }
        }
    };
    container.plug(Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater,
        build_package_diff_update_config);
};


/**
* Add a button to start package diff computation.
*
* @param row {Node} The container node for this package extra infos.
*
* @dsd_link {string} The uri for the distroseriesdifference object.
*/
namespace.setup_request_derived_diff = function(container, dsd_link) {
    // Setup handler for diff requests.
    container.one('.package-diff-compute-request').on('click', function(e) {
        e.preventDefault();
        compute_package_diff(container, dsd_link);
    });
};

/**
* - Add a button to start package diff computation (if needed).
* - Start pollers for pending packages diffs.
*
* @param row {Node} The container node for this package extra infos.
*
* @dsd_link {string} The uri for the distroseriesdifference object.
*/
namespace.setup_packages_diff_states = function(container, dsd_link) {
    // Attach pollers for pending packages diffs.
    container.all('.PENDING').each(function(sub_container){
        namespace.setup_pending_package_diff(sub_container, dsd_link);
    });
    // Find out if there is one package diff that can be requested.
    request_node = container.one('span.request-derived-diff');
    if (request_node !== null) {
        namespace.setup_request_derived_diff(container, dsd_link);
    }
};

/**
* Start package diff computation. Update package diff status to PENDING.
*
* @param row {Node} The container node for this package diff.
*
* @dsd_link {string} The uri for the distroseriesdifference object.
*/
var compute_package_diff = function(container, dsd_link) {
    var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
        'Computing package diff...');
    container.append(in_progress_message);
    container.one('.package-diff-placeholder').set(
        'text',
        'Differences from last common version:');
    var success_cb = function(transaction_id, response, args) {
        container.one('p.update-in-progress-message').remove();
        container.all('.request-derived-diff').each(function(sub_container){
           set_package_diff_status(sub_container, 'PENDING', 'Pending');
           // Setup polling
           namespace.setup_pending_package_diff(sub_container, dsd_link);
           var anim = Y.lazr.anim.green_flash({
               node: sub_container
           });
           anim.run();
        });
    };
    var failure_cb = function(transaction_id, response, args) {
        container.one('p.update-in-progress-message').remove();
        var recompute = function(e) {
            e.preventDefault();
            compute_package_diff(container, dsd_link);
        };

        var msg = response.responseText;

        // If the error is not of the type raised by an error properly
        // raised by python then set a standard error message.
        if (response.status !== 400) {
            msg = 'Failed to compute package diff.';
        }
        var failure_msg = Y.lp.soyuz.base.makeFailureNode(
            Y.Escape.html(msg), recompute);
        var placeholder = container.one('.package-diff-placeholder');
        placeholder.set('innerHTML','');
        placeholder.appendChild(failure_msg);
    };
    var config = {
        on: {
            'success': success_cb,
            'failure': failure_cb
        },
        arguments: {
            'container': container,
            'dsd_link': dsd_link
        }
    };
    lp_client.named_post(dsd_link, 'requestPackageDiffs', config);
};

}, "0.1", {"requires": ["escape", "event-simulate", "io-base",
                        "lp.soyuz.base", "lp.client",
                        "lazr.anim", "lazr.effects",
                        "lp.soyuz.dynamic_dom_updater"]});
