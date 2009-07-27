/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Code for handling links to branches from bugs and specs.
 *
 * @module BranchLinks
 * @requires base, lazr.anim, lazr.formoverlay
 */

YUI.add('code.branchlinks', function(Y) {

Y.branchlinks = Y.namespace('code.branchlinks');

var lp_client;          // The LP client

var link_bug_overlay;

Y.branchlinks.connect_branchlinks = function() {

    link_bug_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Link to a bug</h2>',
        form_content: Y.Node.create(
            '<div id="bugnumberform"></div>'),
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
    Y.io('+linkbug/++form++', {
        on: {
            success: function(id, response) {
                Y.get('#bugnumberform').set(
                    'innerHTML', response.responseText);
            },
            failure: function(id, response) {
                Y.get('#bugnumberform').set(
                    'innerHTML', 'A problem has occurred.');
                Y.log(reponse.responseText);
            }}});

    var linkbug_handle = Y.get('#linkbug');
    linkbug_handle.addClass('js-action');
    linkbug_handle.on('click', function(e) {
        e.preventDefault();
        link_bug_overlay.show();
    });
    connect_remove_links();

};

function connect_remove_links() {
    var linked_bugs = Y.all('.delete-buglink');
    if (Y.Lang.isValue(linked_bugs)) {
        linked_bugs.on('click', function(e) {
            e.preventDefault();
            var bugnumber = get_bugnumber_from_id(e.currentTarget.get('id'));
            unlink_bug_from_branch(bugnumber);
        });
    }
}

function link_bug_to_branch(data) {
    link_bug_overlay.hide();

    create_temporary_spinner();

    var bugnumber = data['field.bug'];
    var existing = Y.get('#buglink-' + bugnumber);
    if (Y.Lang.isValue(existing)) {
        // Bug is already linked, don't do unneccessary requests.
        Y.lazr.anim.green_flash({node: existing}).run();
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
                                add_html_bug(bug, bugtasks);
                            }
                        }
                    };
                    bug.follow_link('bug_tasks', config);
                },
                failure: function(id, response) {
                    alert('An error has occurred : Unable to link bug.');
                    Y.log(response);
                }
            },
            parameters: {
                bug: bug.get('self_link')
            }
        };
        set_up_lp_client();
        lp_client.named_post(
            LP.client.cache.context.self_link, 'linkBug', config);
    });
}

function unlink_bug_from_branch(bugnumber) {
    link_bug_overlay.hide();

    Y.get('#delete-buglink-' + bugnumber).get('children').set(
        'src', '/@@/spinner');
    get_bug_from_bugnumber(bugnumber, function(bug) {

        config = {
            on: {
                success: function(updated_entry) {
                    var element = Y.get('#buglink-' + bugnumber);
                    var parent_element = element.get('parentNode');
                    anim = Y.lazr.anim.red_flash({node: element});
                    anim.on('end', function() {
                        parent_element.removeChild(element);

                        // Check to see if that was the only bug linked.
                        var buglinks = Y.all(".bug-branch-summary");
                        if (!buglinks) {
                            Y.get('#linkbug').set('innerHTML',
                                'Link to a bug report');
                        }
                    });
                    anim.run();
                },
                failure: function(id, response) {
                    alert('An unexpected error has occurred.');
                    Y.get('#delete-buglink-' + bugnumber).get('children').set(
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
            LP.client.cache.context.self_link, 'unlinkBug', config);
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
        lp_client = new LP.client.Launchpad();
    }
}


function add_html_bug(bug, bugtasks) {

    var bugnumber = parseInt(bug.get('id'), 10);
    var bugtitle = bug.get('title').replace('<', '&lt;').replace('>', '&gt;');
    var bugimportance = bugtasks.entries[0].importance;
    var bugstatus = bugtasks.entries[0].status;

    var text = [
        '<div id="buglink-' + bugnumber + '">',
        '<div class="bug-branch-summary">',
        '<a href="/' + bugnumber + '"',
        'class="sprite bug-' + bugimportance.toLowerCase() + '">',
        'Bug #' + bugnumber + ': ' + bugtitle,
        '</a> ',
        '(<span class="importance' + bugimportance.toUpperCase() + '">',
        bugimportance + '</span> &ndash;',
        '<span class="status' + bugstatus.toUpperCase(),
        '">' + bugstatus + '</span>)',
        '<a title="Remove link" class="delete-buglink" href="+bug/',
        bugnumber + '/+delete"',
        'id="delete-buglink-' + bugnumber + '">',
        '<img src="/@@/remove" />',
        '</a>',
        '</div>',
        '</div>'].join('');
    var new_buglink = Y.Node.create(text);

    var buglinks = Y.get('#buglinks');
    var last = Y.get('#linkbug').get('parentNode');
    if (last) {
        buglinks.insertBefore(new_buglink, last);
    }

    var temp_spinner = Y.get('#temp-spinner');
    var spinner_parent = temp_spinner.get('parentNode');
    spinner_parent.removeChild(temp_spinner);

    anim = Y.lazr.anim.green_flash({node: new_buglink});
    anim.run();
    connect_remove_links();
    Y.get("[id='field.bug']").set('value', '');
    Y.get('#linkbug').set('innerHTML', 'Link to another bug');
}


/*
 * Show the temporary "Linking..." text
 */
function create_temporary_spinner() {
    var temp_spinner = Y.Node.create([
        '<div id="temp-spinner">',
        '<img src="/@@/spinner"/>Linking...',
        '</div>'].join(''));
    var buglinks = Y.get('#buglinks');
    var last = Y.get('#linkbug').get('parentNode');
    if (last) {
        buglinks.insertBefore(temp_spinner, last);
    }
}


}, '0.1', {requires: ['base', 'lazr.anim', 'lazr.formoverlay']});
