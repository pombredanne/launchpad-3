/** Copyright (c) 2008, Canonical Ltd. All rights reserved.
 *
 * Auxiliary functions used in Soyuz pages
 *
 * @module soyuz
 * @submodule soyuz-base
 * @namespace soyuz
 * @requires yahoo, node
 */

YUI.add('soyuz-base', function(Y) {

/*
 * Define the 'Y.soyuz' namespace
 */
var soyuz = Y.namespace('soyuz');


/*
 * Return a node containing a standard failure message to be used
 * in XHR-based page updates.
 */
soyuz.makeFailureNode = function (text, handler) {
    var failure_message = Y.Node.create('<p>');
    failure_message.addClass('update-failure-message');

    var message = Y.Node.create('<span>');
    message.set('innerHTML', text);
    failure_message.appendChild(message);

    var retry_link = Y.Node.create('<a>');
    retry_link.addClass('update-retry');
    retry_link.set('href', '');
    retry_link.set('innerHTML', 'Retry');
    retry_link.on('click', handler);
    failure_message.appendChild(retry_link);

    return failure_message;
};


/*
 * Return a node containing a standard in-progress message to be used
 * in XHR-based page updates.
 */
soyuz.makeInProgressNode = function (text) {
    var in_progress_message = Y.Node.create('<p>');
    var message = Y.Node.create('<span>');

    message.set('innerHTML', text);
    in_progress_message.addClass('update-in-progress-message');
    in_progress_message.appendChild(message);

    return in_progress_message;
};

}, '0.1', {requires:['node']});
