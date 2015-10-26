# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Red Hat, Inc.
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

import dci.server.utils
import sample.db_provisioning


def test_dict_merge():
    a = {'jim': 123, 'a': {'b': {'c': {'d': 'bob'}}}, 'rob': 34}
    b = {'tot': {'a': {'b': 'string'}, 'c': [1, 2]}}
    c = {'tot': {'c': [3, 4]}}

    assert dci.server.utils.dict_merge(a, b, c) == {
        'a': {'b': {'c': {'d': 'bob'}}},
        'jim': 123,
        'rob': 34,
        'tot': {'a': {'b': 'string'}, 'c': [1, 2, 3, 4]}
    }


def test_sample_db_provisionning(engine, db_clean):
    """Test the sample init_db method, to be sure it will
    not be broken when updating
    """

    with engine.begin() as db_conn:
        sample.db_provisioning.init_db(db_conn)