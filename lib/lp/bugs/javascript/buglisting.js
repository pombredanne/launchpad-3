/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Client-side rendering of bug listings.
 *
 * @module bugs
 * @submodule buglisting
 */

YUI.add('lp.bugs.buglisting', function(Y) {

var namespace = Y.namespace('lp.bugs.buglisting');

lp_client = new Y.lp.client.Launchpad();

namespace.rendertable = function(){
    client_listing = Y.one('#client-listing');
    if (client_listing === null){
        return;
    }
    var template = '{{#bugtasks}}' +
        '<tr><td><table>' +
        '    <tr><td class={{importance_class}}>{{importance}}</td></tr>' +
        '    <tr><td class={{status_class}}>{{status}}' +
        '</td></tr></table>' +
        '<td><table>' +
        '    <tr><td >#{{id}} <a href="{{bug_url}}">{{title}}</a></td></tr>' +
        '    <tr>' +
        '        <td><span class="{{bugtarget_css}}">{{bugtarget}}</span></td>' +
        '    </tr>' +
        '</table></td>' +
        '<td align="right">{{{badges}}}{{{bug_heat_html}}}</td>' +
        '</tr>' +
        '{{/bugtasks}}';
    var txt = Mustache.to_html(template, LP.cache.mustache_model);
    client_listing.set('innerHTML', txt);
}

}, "0.1", {"requires": ["node"]});
