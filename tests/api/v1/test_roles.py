# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import unicode_literals


def test_success_create_role_admin(admin):
    data = {
        'name': 'Manager',
        'label': 'MANAGER',
        'description': 'A Manager role',
    }

    result = admin.post('/api/v1/roles', data=data)

    assert result.status_code == 201
    assert result.data['role']['name'] == data['name']
    assert result.data['role']['label'] == data['label']
    assert result.data['role']['description'] == data['description']


def test_success_create_role_admin_default_label(admin):
    data = {
        'name': 'Manager',
        'description': 'A Manager role',
    }

    result = admin.post('/api/v1/roles', data=data)

    assert result.status_code == 201
    assert result.data['role']['label'] == data['name'].upper()


def test_fail_create_role_team_admin(user_admin):
    data = {
        'name': 'Manager',
        'label': 'MANAGER',
        'description': 'A Manager role',
    }

    result = user_admin.post('/api/v1/roles', data=data)

    assert result.status_code == 401


def test_fail_create_role_user(user):
    data = {
        'name': 'Manager',
        'label': 'MANAGER',
        'description': 'A Manager role',
    }

    result = user.post('/api/v1/roles', data=data)

    assert result.status_code == 401


def test_success_create_role_correct_payload(admin):
    data = {
        'name': 'Manager',
        'label': 'MANAGER',
        'description': 'A Manager role',
    }

    result = admin.post('/api/v1/roles', data=data)

    assert result.status_code == 201


def test_fail_ensure_payload_content_is_checked(admin):
    data = {
        'description': 'A Manager role',
    }

    result = admin.post('/api/v1/roles', data=data)

    assert result.status_code == 400


def test_fail_create_role_already_exists(admin):
    data = {
        'name': 'Manager',
        'label': 'MANAGER',
        'description': 'A Manager role',
    }

    result = admin.post('/api/v1/roles', data=data)
    assert result.status_code == 201
    result = admin.post('/api/v1/roles', data=data)
    assert result.status_code == 409


def test_success_update_role(admin, role):
    role_id = role['id']

    url = '/api/v1/roles/%s' % role_id
    assert role['name'] == 'Manager'

    result = admin.put(url, data={'name': 'User'},
                       headers={'If-match': role['etag']})
    assert result.status_code == 204

    role = admin.get(url).data
    assert role['role']['name'] == 'User'
    assert role['role']['description'] == 'A Manager role'

    result = admin.put(url, data={'description': 'new role'},
                       headers={'If-match': role['role']['etag']})
    assert result.status_code == 204

    role = admin.get(url).data
    assert role['role']['name'] == 'User'
    assert role['role']['description'] == 'new role'


def test_fail_update_role_label(admin, role):
    url = '/api/v1/roles/%s' % role['id']

    result = admin.put(url, data={'label': 'MANAGER_UPDATE'},
                       headers={'If-match': role['etag']})

    assert result.status_code == 400


def test_fail_update_role_unauthorized_fields(admin, role):
    label = {
        'label': 'NEW LABEL',
    }

    result = admin.put('/api/v1/roles/%s' % role['id'], data=label,
                       headers={'If-match': role['etag']})

    assert result.status_code == 400


def test_success_get_role_by_id(admin, role):
    result = admin.get('/api/v1/roles/%s' % role['id'])

    assert result.status_code == 200
    assert result.data['role']['name'] == 'Manager'


def test_failure_get_super_admin_role_by_id(admin, user_admin, user):
    result = admin.get('/api/v1/roles?where=label:SUPER_ADMIN')

    assert result.status_code == 200
    super_admin_role_id = result.data['roles'][0]['id']

    ua_request = user_admin.get('/api/v1/roles/%s' % super_admin_role_id)
    assert ua_request.status_code == 401

    u_request = user.get('/api/v1/roles/%s' % super_admin_role_id)
    assert u_request.status_code == 401


def test_failure_get_not_my_role_by_id(user, role):
    result = user.get('/api/v1/roles/%s' % role['id'])

    assert result.status_code == 401

    result = user.get('/api/v1/roles?where=label:USER')

    assert result.status_code == 200

    my_role_id = result.data['roles'][0]['id']
    result = user.get('/api/v1/roles/%s' % my_role_id)
    assert result.status_code == 200
    assert result.data['role']['label'] == 'USER'


def test_success_get_all_roles_admin(admin):
    result = admin.get('/api/v1/roles')

    assert result.status_code == 200

    roles = [r['label'] for r in result.data['roles']]
    assert ['ADMIN', 'FEEDER', 'PRODUCT_OWNER', 'REMOTECI',
            'SUPER_ADMIN', 'USER'] == sorted(roles)


def test_success_get_all_roles_user_admin(user_admin):
    result = user_admin.get('/api/v1/roles')

    assert result.status_code == 200

    roles = [r['label'] for r in result.data['roles']]
    assert ['ADMIN', 'FEEDER', 'REMOTECI', 'USER'] == sorted(roles)


def test_failure_get_all_roles_user(user):
    result = user.get('/api/v1/roles')

    assert result.status_code == 200

    roles = [r['label'] for r in result.data['roles']]
    assert ['USER'] == sorted(roles)


def test_success_delete_role_admin(admin, role):
    result = admin.get('/api/v1/roles')
    roles = [r['label'] for r in result.data['roles']]

    assert ['ADMIN', 'FEEDER', 'MANAGER', 'PRODUCT_OWNER',
            'REMOTECI', 'SUPER_ADMIN', 'USER'] == sorted(roles)

    result = admin.delete('/api/v1/roles/%s' % role['id'],
                          headers={'If-match': role['etag']})

    assert result.status_code == 204

    result = admin.get('/api/v1/roles')
    roles = [r['label'] for r in result.data['roles']]
    assert ['ADMIN', 'FEEDER', 'PRODUCT_OWNER', 'REMOTECI',
            'SUPER_ADMIN', 'USER'] == sorted(roles)


def test_fail_delete_role_user(user, role):
    result = user.delete('/api/v1/roles/%s' % role['id'],
                         headers={'If-match': role['etag']})

    assert result.status_code == 401


def test_success_add_permission_to_role_admin(admin, role, permission):
    data = {
        'permission_id': permission['id']
    }

    result = admin.post('/api/v1/roles/%s/permissions' % role['id'],
                        data=data)
    assert result.status_code == 201

    result = admin.get('/api/v1/roles/%s?embed=permissions' % role['id'])
    assert result.data['role']['permissions'][0]['label'] == 'APERMISSION'


def test_fail_add_permission_to_role_user_admin(user_admin, role, permission):
    data = {
        'permission_id': permission['id']
    }

    result = user_admin.post('/api/v1/roles/%s/permissions' % role['id'],
                             data=data)
    assert result.status_code == 401


def test_fail_add_permission_to_role_user(user, role, permission):
    data = {
        'permission_id': permission['id']
    }

    result = user.post('/api/v1/roles/%s/permissions' % role['id'], data=data)
    assert result.status_code == 401


def test_success_remove_permission_from_role_admin(admin, role, permission):
    data = {
        'permission_id': permission['id']
    }

    result = admin.post('/api/v1/roles/%s/permissions' % role['id'],
                        data=data)
    assert result.status_code == 201

    result = admin.get('/api/v1/roles/%s?embed=permissions' % role['id'])
    assert result.data['role']['permissions'][0]['label'] == 'APERMISSION'

    result = admin.delete('/api/v1/roles/%s/permissions/%s' %
                          (role['id'], permission['id']))
    assert result.status_code == 204

    result = admin.get('/api/v1/roles/%s?embed=permissions' % role['id'])
    assert len(result.data['role']['permissions']) == 0


def test_fail_remove_permission_from_role_user_admin(admin, user_admin,
                                                     role, permission):
    data = {
        'permission_id': permission['id']
    }

    result = admin.post('/api/v1/roles/%s/permissions' % role['id'],
                        data=data)
    assert result.status_code == 201

    result = admin.get('/api/v1/roles/%s?embed=permissions' % role['id'])
    assert result.data['role']['permissions'][0]['label'] == 'APERMISSION'

    result = user_admin.delete('/api/v1/roles/%s/permissions/%s' %
                               (role['id'], permission['id']))
    assert result.status_code == 401

    result = admin.get('/api/v1/roles/%s?embed=permissions' % role['id'])
    assert len(result.data['role']['permissions']) == 1


def test_fail_remove_permission_from_role_user(admin, user,
                                               role, permission):
    data = {
        'permission_id': permission['id']
    }

    result = admin.post('/api/v1/roles/%s/permissions' % role['id'],
                        data=data)
    assert result.status_code == 201

    result = admin.get('/api/v1/roles/%s?embed=permissions' % role['id'])
    assert result.data['role']['permissions'][0]['label'] == 'APERMISSION'

    result = user.delete('/api/v1/roles/%s/permissions/%s' %
                         (role['id'], permission['id']))
    assert result.status_code == 401

    result = admin.get('/api/v1/roles/%s?embed=permissions' % role['id'])
    assert result.data['role']['permissions'][0]['label'] == 'APERMISSION'
