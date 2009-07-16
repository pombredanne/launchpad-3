/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Library for code review javascript.
 *
 * @module CodeReview
 * @requires base, lazr.anim, lazr.formoverlay
 */

YUI.add('code.codereview', function(Y) {

Y.codereview = Y.namespace('code.codereview');

Y.codereview.connect_links = function() {

    var link = Y.get('#request-review');
    link.addClass('js-action');
    link.on('click', show_request_review_form);

};

function show_request_review_form(e) {

    e.preventDefault();
    alert('show_request_review_form');
}


}, '0.1', {requires: ['base', 'lazr.anim', 'lazr.formoverlay']});
