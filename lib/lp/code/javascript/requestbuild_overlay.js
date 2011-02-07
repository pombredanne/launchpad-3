/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * A form overlay that can request builds for a recipe..
 *
 * @namespace Y.lp.code.recipebuild_overlay
 * @requires  dom, node, io-base, lazr.anim, lazr.formoverlay
 */
YUI.add('lp.code.requestbuild_overlay', function(Y) {
Y.log('loading lp.code.requestbuild_overlay');

var namespace = Y.namespace('lp.code.requestbuild_overlay');

var lp_client;
var request_build_overlay;
var error_handler;

function set_up_lp_client() {
    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }
}

/*
 * Connect the links to the javascript events.
 */

namespace.connect_requestbuild = function(config) {

    error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = function() {
        destroy_temporary_spinner();
    };
    error_handler.showError = function(error_message) {
        destroy_temporary_spinner();
        alert('An unexpected error has occurred.');
        Y.log(error_message);
    };

    if (config === undefined) {
        throw new Error(
            "Missing connect_requestbuild config for requestbuild_overlay.");
    }


    request_build_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Request builds for ' + config.recipe_name + ' </h2>',
        form_submit_button: Y.Node.create(
            '<button type="submit" name="field.actions.request" ' +
            'value="Request builds" class="lazr-pos lazr-btn">Ok</button>'),
        form_cancel_button: Y.Node.create(
            '<button type="button" name="field.actions.cancel" ' +
            'class="lazr-neg lazr-btn">Cancel</button>'),
        centered: true,
        form_submit_callback: do_request_builds,
        visible: false
    });
    request_build_overlay.render();
    request_build_overlay.loadFormContentAndRender('+request-builds/++form++');
    var request_build_handle = Y.one('#request-builds');
    request_build_handle.addClass('js-action');
    request_build_handle.on('click', function(e) {
        e.preventDefault();
        request_build_overlay.show();
    });
};

function do_request_builds(data) {
    request_build_overlay.hide();
    create_temporary_spinner();

    var client = this;
    var base_url = LP.client.cache.context.self_link.replace('/api/devel', '');
    var uri = '+request-builds'; //uri is used later
    var submit_url = base_url+"/"+uri;
    var next_url = base_url+"/+builds";
    var query_str = '';
    query_str = LP.client.append_qs(query_str, 'field.archive', data['field.archive']);
    query_str = LP.client.append_qs(query_str, 'field.distros', data['field.distros']);
    query_str = LP.client.append_qs(query_str, 'field.actions.request', 'Request builds');
    query_str = LP.client.append_qs(query_str, 'next_url', next_url);

    var y_config = {
                     method: "POST",
                     headers: {'Accept': 'application/json'},
            on: {
                success: function(id, response) {
//                    var new_build_id = 2;
                    var target = Y.one('#builds-target');
                    target.set('innerHTML', response.responseText);
//                    var new_build = Y.one('#build-' + new_build_id);
//                    var anim = Y.lazr.anim.green_flash({node: new_build});
//                    anim.run();

                    destroy_temporary_spinner();
                },
                failure: function(id, response, args) {
                    // If we have firebug installed, log the error.
                    if( console != undefined ) {
                        console.log("Request Build Error: " + args + ': '
                                + response.status + ' - ' +
                                response.statusText + ' - '
                                + response.responseXML);
                    }
                }
                //failure: error_handler.getFailureHandler()
            },
         arguments: [client, uri],
         data: query_str

    };
    Y.io(submit_url, y_config);
}

/*
 * Show the temporary "Requesting..." text
 */
function create_temporary_spinner() {
    // Add the temp "Requesting build..." text
    var temp_spinner = Y.Node.create([
        '<div id="temp-spinner">',
        '<img src="/@@/spinner"/>Requesting build...',
        '</div>'].join(''));
    var request_build_handle = Y.one('#request-builds');
    request_build_handle.insert(temp_spinner, request_build_handle);
}

/*
 * Destroy the temporary "Requesting..." text
 */
function destroy_temporary_spinner() {
    var temp_spinner = Y.one('#temp-spinner');
    var spinner_parent = temp_spinner.get('parentNode');
    spinner_parent.removeChild(temp_spinner);
}

}, "0.1", {"requires": [
    "dom", "node", "io-base", "lazr.anim", "lazr.formoverlay",
    "lp.client.plugins"
    ]});
