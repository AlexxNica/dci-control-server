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

import flask
from flask import json
from sqlalchemy import exc as sa_exc
from sqlalchemy import sql

from dci.api.v1 import api
from dci.api.v1 import base
from dci.api.v1 import utils as v1_utils
from dci import auth
from dci import decorators
from dci.common import exceptions as dci_exc
from dci.common import schemas
from dci.common import signature
from dci.common import utils
from dci.db import embeds
from dci.db import models

_TABLE = models.FEEDERS
_F_COLUMNS = v1_utils.get_columns_name_with_objects(_TABLE)
_VALID_EMBED = embeds.feeders()
_EMBED_MANY = {
    'team': False,
}


@api.route('/feeders', methods=['POST'])
@decorators.login_required
@decorators.has_role(['SUPER_ADMIN', 'PRODUCT_OWNER'])
def create_feeders(user):
    values = v1_utils.common_values_dict(user)
    values.update(schemas.feeder.post(flask.request.json))

    if not user.is_in_team(values['team_id']):
        raise auth.UNAUTHORIZED

    values.update({
        # XXX(fc): this should be populated as a default value from the
        # model, but we don't return values from the database :(
        'api_secret': signature.gen_secret(),
        'role_id': auth.get_role_id('FEEDER'),
        'data': values.get('data', {}),
    })

    query = _TABLE.insert().values(**values)

    try:
        flask.g.db_conn.execute(query)
    except sa_exc.IntegrityError:
        raise dci_exc.DCICreationConflict(_TABLE.name, 'name')

    return flask.Response(
        json.dumps({'feeder': values}), 201,
        headers={'ETag': values['etag']}, content_type='application/json'
    )


@api.route('/feeders', methods=['GET'])
@decorators.login_required
@decorators.has_role(['SUPER_ADMIN', 'PRODUCT_OWNER'])
def get_all_feeders(user):
    args = schemas.args(flask.request.args.to_dict())

    query = v1_utils.QueryBuilder(_TABLE, args, _F_COLUMNS)

    if not user.is_super_admin():
        query.add_extra_condition(_TABLE.c.team_id.in_(user.teams))

    query.add_extra_condition(_TABLE.c.state != 'archived')

    rows = query.execute(fetchall=True)
    rows = v1_utils.format_result(rows, _TABLE.name, args['embed'],
                                  _EMBED_MANY)

    return flask.jsonify({'feeders': rows, '_meta': {'count': len(rows)}})


@api.route('/feeders/<uuid:f_id>', methods=['GET'])
@decorators.login_required
@decorators.has_role(['SUPER_ADMIN', 'PRODUCT_OWNER'])
def get_feeder_by_id(user, f_id):
    feeder = v1_utils.verify_existence_and_get(f_id, _TABLE)
    if not user.is_in_team(feeder['team_id']):
        raise auth.UNAUTHORIZED
    return base.get_resource_by_id(user, feeder, _TABLE, _EMBED_MANY)


@api.route('/feeders/<uuid:f_id>', methods=['PUT'])
@decorators.login_required
@decorators.has_role(['SUPER_ADMIN', 'PRODUCT_OWNER'])
def put_feeder(user, f_id):
    if_match_etag = utils.check_and_get_etag(flask.request.headers)
    values = schemas.feeder.put(flask.request.json)
    feeder = v1_utils.verify_existence_and_get(f_id, _TABLE)

    if not user.is_in_team(feeder['team_id']):
        raise auth.UNAUTHORIZED

    values['etag'] = utils.gen_etag()
    where_clause = sql.and_(_TABLE.c.etag == if_match_etag,
                            _TABLE.c.state != 'archived',
                            _TABLE.c.id == f_id)

    query = (_TABLE
             .update()
             .where(where_clause)
             .values(**values))

    result = flask.g.db_conn.execute(query)

    if not result.rowcount:
        raise dci_exc.DCIConflict('Feeder', f_id)

    return flask.Response(None, 204, headers={'ETag': values['etag']},
                          content_type='application/json')


@api.route('/feeders/<uuid:f_id>', methods=['DELETE'])
@decorators.login_required
@decorators.has_role(['SUPER_ADMIN', 'PRODUCT_OWNER'])
def delete_feeder_by_id(user, f_id):
    if_match_etag = utils.check_and_get_etag(flask.request.headers)
    feeder = v1_utils.verify_existence_and_get(f_id, _TABLE)

    if not user.is_in_team(feeder['team_id']):
        raise auth.UNAUTHORIZED

    with flask.g.db_conn.begin():
        values = {'state': 'archived'}
        where_clause = sql.and_(
            _TABLE.c.etag == if_match_etag,
            _TABLE.c.id == f_id
        )
        query = _TABLE.update().where(where_clause).values(**values)

        result = flask.g.db_conn.execute(query)

        if not result.rowcount:
            raise dci_exc.DCIDeleteConflict('Feeder', f_id)

    return flask.Response(None, 204, content_type='application/json')


@api.route('/feeders/purge', methods=['GET'])
@decorators.login_required
@decorators.has_role(['SUPER_ADMIN'])
def get_to_purge_archived_feeders(user):
    return base.get_to_purge_archived_resources(user, _TABLE)


@api.route('/feeders/purge', methods=['POST'])
@decorators.login_required
@decorators.has_role(['SUPER_ADMIN'])
def purge_archived_feeders(user):
    return base.purge_archived_resources(user, _TABLE)


@api.route('/feeders/<uuid:f_id>/api_secret', methods=['PUT'])
@decorators.login_required
@decorators.has_role(['SUPER_ADMIN', 'PRODUCT_OWNER'])
def put_api_secret_feeder(user, f_id):
    utils.check_and_get_etag(flask.request.headers)
    feeder = v1_utils.verify_existence_and_get(f_id, _TABLE)
    if not user.is_in_team(feeder['team_id']):
        raise auth.UNAUTHORIZED

    return base.refresh_api_secret(user, feeder, _TABLE)
