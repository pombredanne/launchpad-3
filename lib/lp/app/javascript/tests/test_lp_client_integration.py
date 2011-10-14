# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""{Describe your test suite here}.
"""

__metaclass__ = type
__all__ = []

from lp.testing import person_logged_in
from lp.testing.yuixhr import (
    login_as_person,
    make_suite,
    setup,
    )
from lp.testing.factory import LaunchpadObjectFactory

factory = LaunchpadObjectFactory()

@setup
def create_user(request, data):
    data['user'] = factory.makePerson()


@create_user.extend
def create_user_and_login(request, data):
    login_as_person(data['user'])


@create_user.extend
def create_product(request, data):
    with person_logged_in(data['user']):
        data['product'] = factory.makeProduct(owner=data['user'])


@create_product.extend
def create_product_and_login(request, data):
    login_as_person(data['user'])


@create_product_and_login.extend
def create_bug_and_login(request, data):
    data['bug'] = factory.makeBug(
        product=data['product'], owner=data['user'])
    data['bugtask'] = data['bug'].bugtasks[0]


@setup
def login_as_admin(request, data):
    data['admin'] = factory.makeAdministrator();
    login_as_person(data['admin'])


@setup
def create_user_with_html_display_name(request, data):
    data['user'] = factory.makePerson(
        displayname='<strong>naughty</strong>')


def test_suite():
    return make_suite(__name__)
