/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code for handling links to branches from bugs and specs.
 *
 * @module BranchLinks
 * @requires base, lp.anim, lazr.formoverlay
 */

YUI.add('lp.code.branch.bugspeclinks', function(Y) {

var namespace = Y.namespace('lp.code.branch.bugspeclinks');

var lp_client;          // The LP client

var link_bug_overlay;

var error_handler;

/*
 * Extract the best candidate for a bug number from the branch name.
 */
function extract_candidate_bug_id(branch_name) {
    // Extract all the runs of numbers in the branch name and sort by
    // descending length.
    var chunks = branch_name.split(/\D/g).sort(function (a, b) {
        return b.length - a.length;
    });
    var chunk, i;
    for (i=0; i<chunks.length; i++) {
        chunk = chunks[i];
        // Bugs with fewer than six digits aren't being created any more (by
        // Canonical's LP at least), but there are lots of open five digit
        // bugs so ignore runs of fewer than five digits in the branch name.
        if (chunk.length < 5) {
            break;
        }
        // Bug IDs don't start with a zero.
        if (chunk[0] !== '0') {
            return chunk;
        }
    }
    return null;
}
// Expose in the namespace so we can test it.
namespace._extract_candidate_bug_id = extract_candidate_bug_id;

/*
 * Connect the links to the javascript events.
 */
namespace.connect_branchlinks = function() {

    error_handler = new Y.lp.client.ErrorHandler();
    error_handler.clearProgressUI = function() {
        destroy_temporary_spinner();
    };
    error_handler.showError = function(error_message) {
        alert('An unexpected error has occurred.');
        Y.log(error_message);
    };

    link_bug_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Link to a bug</h2>',
        form_submit_button: Y.Node.create(
            '<button type="submit" name="buglink.actions.change" ' +
            'value="Change" class="lazr-pos lazr-btn">Ok</button>'),
        form_cancel_button: Y.Node.create(
            '<button type="button" name="buglink.actions.cancel" ' +
            'class="lazr-neg lazr-btn">Cancel</button>'),
        centered: true,
        form_submit_callback: link_bug_to_branch,
        visible: false
    });
    link_bug_overlay.render();
    link_bug_overlay.loadFormContentAndRender('+linkbug/++form++');
    var linkbug_handle = Y.one('#linkbug');
    linkbug_handle.addClass('js-action');
    linkbug_handle.on('click', function(e) {
        e.preventDefault();
        link_bug_overlay.show();
        var field = Y.DOM.byId('field.bug');
        field.focus();
        var guessed_bug_id = extract_candidate_bug_id(LP.cache.context.name);
        if (Y.Lang.isValue(guessed_bug_id)) {
            field.value = guessed_bug_id;
            // Select the pre-filled bug number (if any) so that it will be
            // replaced by anything the user types (getting the guessed bug
            // number out of the way quickly if we guessed incorrectly).
            field.selectionStart = 0;
            field.selectionEnd = 999;
        }
    });
    connect_remove_links();
};

/*
 * Connect the remove links of each bug link to the javascript functions to
 * remove the links.
 */
function connect_remove_links() {
    Y.on('click', function(e) {
        e.preventDefault();
        var bugnumber = get_bugnumber_from_id(e.currentTarget.get('id'));
        unlink_bug_from_branch(bugnumber);
    }, '.delete-buglink');
}

/*
 * Link a specified bug to the branch.
 */
function link_bug_to_branch(data) {
    link_bug_overlay.hide();

    create_temporary_spinner();

    var bugnumber = data['field.bug'];
    var existing = Y.one('#buglink-' + bugnumber);
    if (Y.Lang.isValue(existing)) {
        // Bug is already linked, don't do unneccessary requests.
        Y.lp.anim.green_flash({node: existing}).run();
        return;
    }

    get_bug_from_bugnumber(bugnumber, function(bug) {

        config = {
            on: {
                success: function(entry) {
                    // XXX: rockstar - linkBug still is returning BugBranches.
                    // This means that I'll need to change this once I fix
                    // that.
                    var config = {
                        on: {
                            success: function(bugtasks) {
                                update_bug_links(bug);
                            }
                        }
                    };
                    bug.follow_link('bug_tasks', config);
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                bug: bug.get('self_link')
            }
        };
        set_up_lp_client();
        lp_client.named_post(
            LP.cache.context.self_link, 'linkBug', config);
    });
}

/*
 * Update the list of bug links.
 */
function update_bug_links(bug) {

    BUG_LINK_SNIPPET = '++bug-links';
    Y.io(BUG_LINK_SNIPPET, {
        on: {
            success: function(id, response) {
                destroy_temporary_spinner();
                Y.one('#linkbug')
                    .set('innerHTML', 'Link to another bug report');
                Y.one('#buglink-list')
                    .set('innerHTML', response.responseText);
                var new_buglink = Y.one('#buglink-' + bug.get('id'));
                var anim = Y.lp.anim.green_flash({node: new_buglink});
                anim.on('end', connect_remove_links);
                anim.run();
            },
            failure: function(id, response) {
                // At least remove the "Linking..." text
                destroy_temporary_spinner();

                alert('Unable to update bug links.');
                Y.log(response);
            }
        }
    });

}

/*
 * Unlink a bug from the branch.
 */
function unlink_bug_from_branch(bugnumber) {
    link_bug_overlay.hide();

    Y.one('#delete-buglink-' + bugnumber).get('children').set(
        'src', '/@@/spinner');
    get_bug_from_bugnumber(bugnumber, function(bug) {

        config = {
            on: {
                success: function(updated_entry) {
                    var element = Y.one('#buglink-' + bugnumber);
                    var parent_element = element.get('parentNode');
                    anim = Y.lp.anim.red_flash({node: element});
                    anim.on('end', function() {
                        parent_element.removeChild(element);

                        // Check to see if that was the only bug linked.
                        var buglinks = Y.all(".bug-branch-summary");
                        if (!buglinks.size()) {
                            Y.one('#linkbug').set('innerHTML',
                                'Link to a bug report');
                        }
                    });
                    anim.run();
                },
                failure: function(id, response) {
                    alert('An unexpected error has occurred.');
                    Y.one('#delete-buglink-' + bugnumber).get('children').set(
                        'src', '/@@/remove');
                    Y.log(response.responseText);
                }
            },
            parameters: {
                bug: bug.get('self_link')
            }
        };
        set_up_lp_client();
        lp_client.named_post(
            LP.cache.context.self_link, 'unlinkBug', config);
    });
}


/*
 * Get the bugnumber for the element id.
 *
 * Since we control the element id, we don't have to use crazy reqexes or
 * something.
 */
function get_bugnumber_from_id(id) {
    return id.substr('remove-buglink-'.length, id.length);
}

/*
 * Get the bug representation from the bugnumber.
 *
 * XXX: rockstar - There is a better way to do this, I'm sure.  I just need to
 * figure it out after everything else is done.
 */
function get_bug_from_bugnumber(bugnumber, callback) {
    var bug_uri = '/bugs/' + bugnumber;
    config = {
        on: {
            success: callback
        }
    };
    set_up_lp_client();
    lp_client.get(bug_uri, config);
}

/*
 * Set up the lp_client.
 *
 * This would probably be better served in a place where everyone could get to
 * it, or at least so everything in code could get to it.
 */
function set_up_lp_client() {
    if (lp_client === undefined) {
        lp_client = new Y.lp.client.Launchpad();
    }
}

/*
 * Show the temporary "Linking..." text
 */
function create_temporary_spinner() {
    var temp_spinner = Y.Node.create([
        '<div id="temp-spinner">',
        '<img src="/@@/spinner"/>Linking...',
        '</div>'].join(''));
    var buglinks = Y.one('#buglinks');
    var last = Y.one('#linkbug').get('parentNode');
    if (last) {
        buglinks.insertBefore(temp_spinner, last);
    }
}

/*
 * Destroy the temporary "Linking..." text
 */
function destroy_temporary_spinner() {

    var temp_spinner = Y.one('#temp-spinner');
    var spinner_parent = temp_spinner.get('parentNode');
    spinner_parent.removeChild(temp_spinner);

}

}, "0.1", {"requires": ["base", "lp.anim", "lazr.formoverlay",
                        "lp.client", "lp.client.plugins"]});
