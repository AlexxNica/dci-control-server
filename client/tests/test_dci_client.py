# -*- encoding: utf-8 -*-
#
# Copyright 2015 Red Hat, Inc.
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

import mock
import testtools

import client.dci_client as client


class TestClient(testtools.TestCase):
    def setUp(self):
        super(TestClient, self).setUp()
        self.print_call = []

    def _catch_print_call(self, a):
        self.print_call.append(str(a))

    def test_main_list(self):
        response = mock.Mock()
        response.json.return_value = {'_items': [
            {'id': 'id', 'name': 'name',
             'created_at': 'created_at', 'updated_at': 'updated_at'}]}
        client.requests.get = mock.Mock(return_value=response)
        setattr(client, 'print', self._catch_print_call)
        client.main(args=['list', '--remotecis'])
        self.assertEqual([
            "args: ['list', '--remotecis']",
            '+------------+------+------------+------------+\n'
            '| identifier | name | created_at | updated_at |\n'
            '+------------+------+------------+------------+\n'
            '|     id     | name | created_at | updated_at |\n'
            '+------------+------+------------+------------+'],
            self.print_call)

    def test_main_registerci(self):
        response = mock.Mock()
        response.json.return_value = {'_items': [
            {'id': 'id', 'name': 'name',
             'created_at': 'created_at', 'updated_at': 'updated_at'}]}
        client.requests.post = mock.Mock(return_value=response)
        setattr(client, 'print', self._catch_print_call)
        client.main(args=['register-remoteci', '--name', 'bob'])
        self.assertEqual([
            "args: ['register-remoteci', '--name', 'bob']",
            "RemoteCI 'bob' created successfully."], self.print_call)

    def test_main_auto(self):
        response = mock.Mock()
        response.json.return_value = {
            'id': 'bob',
            'job_id': 'bobo',
            'data': {'ksgen_args': {}},
            '_status': 'OK'
        }
        client.requests.get = mock.Mock(return_value=response)
        client.requests.post = mock.Mock(return_value=response)
        popenobj = mock.Mock()
        popenobj.returncode = 0
        client.subprocess = mock.Mock()
        client.subprocess.Popen.return_value = popenobj
        client.main(args=['auto', 'some-remoteci-id'])
        self.assertEqual(self.print_call, [])
