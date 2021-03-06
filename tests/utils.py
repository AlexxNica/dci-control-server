# -*- encoding: utf-8 -*-
#
# Copyright 2015-2016 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

try:
    from urlparse import parse_qsl
    from urlparse import urlparse
except ImportError:
    from urllib.parse import parse_qsl
    from urllib.parse import urlparse
import base64
import collections
import flask
import shutil

import mock
import six

import dci.auth as auth
import dci.common.utils as utils
import dci.db.models as models
import dci.dci_config as config
from dci.stores.swift import Swift
from dciauth.request import AuthRequest
from dciauth.signature import Signature

import os
import subprocess

# convenient alias
memoized = utils.memoized
conf = config.generate_conf()


def restore_db(engine):
    models.metadata.drop_all(engine)
    models.metadata.create_all(engine)


def rm_upload_folder():
    shutil.rmtree(conf['FILES_UPLOAD_FOLDER'], ignore_errors=True)


def generate_client(app, credentials=None, access_token=None):
    attrs = ['status_code', 'data', 'headers']
    Response = collections.namedtuple('Response', attrs)

    if credentials:
        token = (base64.b64encode(('%s:%s' % credentials).encode('utf8'))
                 .decode('utf8'))
        headers = {
            'Authorization': 'Basic ' + token,
            'Content-Type': 'application/json'
        }
    elif access_token:
        headers = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json'
        }

    def client_open_decorator(func):
        def wrapper(*args, **kwargs):
            headers.update(kwargs.get('headers', {}))
            kwargs['headers'] = headers
            content_type = headers.get('Content-Type')
            data = kwargs.get('data')
            if data and content_type == 'application/json':
                kwargs['data'] = flask.json.dumps(data, cls=utils.JSONEncoder)
            response = func(*args, **kwargs)

            data = response.data
            if response.content_type == 'application/json':
                data = flask.json.loads(data or '{}')
            if type(data) == six.binary_type:
                data = data.decode('utf8')

            return Response(response.status_code, data, response.headers)

        return wrapper

    client = app.test_client()
    client.open = client_open_decorator(client.open)

    return client


def generate_token_based_client(app, resource):
    attrs = ['status_code', 'data', 'headers']
    Response = collections.namedtuple('Response', attrs)
    headers = {'Content-Type': 'application/json'}

    def client_open_decorator(func):
        def wrapper(*args, **kwargs):
            headers.update(kwargs.get('headers', {}))
            payload = kwargs.get('data')
            url = urlparse(args[0])
            params = dict(parse_qsl(url.query))
            auth_request = AuthRequest(
                method=kwargs.get('method'),
                endpoint=url.path,
                payload=payload,
                headers=headers,
                params=params
            )
            signature = Signature(request=auth_request)
            kwargs['headers'] = signature.generate_headers(
                client_id=resource['id'],
                client_type=resource['type'],
                secret=resource['api_secret']
            )
            if payload:
                json = flask.json.dumps(payload, cls=utils.JSONEncoder)
                kwargs['data'] = json
            response = func(*args, **kwargs)
            data = flask.json.loads(response.data or '{}')
            return Response(response.status_code, data, response.headers)
        return wrapper

    client = app.test_client()
    client.open = client_open_decorator(client.open)
    return client


def provision(db_conn):
    def db_insert(model_item, **kwargs):
        query = model_item.insert().values(**kwargs)
        return db_conn.execute(query).inserted_primary_key[0]

    user_pw_hash = auth.hash_password('user')
    user_admin_pw_hash = auth.hash_password('user_admin')
    product_owner_pw_hash = auth.hash_password('product_owner')
    admin_pw_hash = auth.hash_password('admin')

    # Create teams
    team_admin_id = db_insert(models.TEAMS, name='admin')
    team_product_id = db_insert(models.TEAMS, name='product')
    team_user_id = db_insert(models.TEAMS, name='user',
                             parent_id=team_product_id)

    # Create the three mandatory roles
    super_admin_role = {
        'name': 'Super Admin',
        'label': 'SUPER_ADMIN',
        'description': 'Admin of the platform',
    }

    product_owner_role = {
        'name': 'Product Owner',
        'label': 'PRODUCT_OWNER',
        'description': 'Product Owner',
    }

    admin_role = {
        'name': 'Admin',
        'label': 'ADMIN',
        'description': 'Admin of a team',
    }

    user_role = {
        'name': 'User',
        'label': 'USER',
        'description': 'Regular User',
    }

    remoteci_role = {
        'name': 'RemoteCI',
        'label': 'REMOTECI',
        'description': 'A RemoteCI',
    }

    feeder_role = {
        'name': 'Feeder',
        'label': 'FEEDER',
        'description': 'A Feeder',
    }

    admin_role_id = db_insert(models.ROLES, **admin_role)
    user_role_id = db_insert(models.ROLES, **user_role)
    super_admin_role_id = db_insert(models.ROLES, **super_admin_role)
    product_owner_role_id = db_insert(models.ROLES, **product_owner_role)
    db_insert(models.ROLES, **remoteci_role)
    db_insert(models.ROLES, **feeder_role)

    # Create users
    db_insert(models.USERS,
              name='user',
              sso_username='user',
              role_id=user_role_id,
              password=user_pw_hash,
              fullname='User',
              email='user@example.org',
              team_id=team_user_id)

    db_insert(models.USERS,
              name='user_admin',
              sso_username='user_admin',
              role_id=admin_role_id,
              password=user_admin_pw_hash,
              fullname='User Admin',
              email='user_admin@example.org',
              team_id=team_user_id)

    db_insert(models.USERS,
              name='product_owner',
              sso_username='product_owner',
              role_id=product_owner_role_id,
              password=product_owner_pw_hash,
              fullname='Product Owner',
              email='product_ownern@example.org',
              team_id=team_product_id)

    db_insert(models.USERS,
              name='admin',
              sso_username='admin',
              role_id=super_admin_role_id,
              password=admin_pw_hash,
              fullname='Admin',
              email='admin@example.org',
              team_id=team_admin_id)

    # Create a product
    db_insert(models.PRODUCTS,
              name='Awesome product',
              label='AWSM',
              description='My Awesome product',
              team_id=team_product_id)


SWIFT = 'dci.stores.swift.Swift'

FileDesc = collections.namedtuple('FileDesc', ['name', 'content'])


def post_file(client, jobstate_id, file_desc):
    with mock.patch(SWIFT, spec=Swift) as mock_swift:

        mockito = mock.MagicMock()

        head_result = {
            'etag': utils.gen_etag(),
            'content-type': "stream",
            'content-length': 7
        }

        mockito.head.return_value = head_result
        mock_swift.return_value = mockito
        headers = {'DCI-JOBSTATE-ID': jobstate_id, 'DCI-NAME': file_desc.name,
                   'Content-Type': 'text/plain',
                   'DCI-MIME': 'text/plain'}
        res = client.post('/api/v1/files',
                          headers=headers,
                          data=file_desc.content)

        return res.data['file']['id']


def run_bin(bin_name, env):
    env.update(os.environ.copy())
    exec_path = os.path.abspath(__file__)
    exec_path = os.path.abspath('%s/../../bin/%s' % (exec_path, bin_name))
    return subprocess.Popen(exec_path, shell=True, env=env)
