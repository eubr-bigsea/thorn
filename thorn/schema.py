# -*- coding: utf-8 -*-
import datetime
import json
from copy import deepcopy
from marshmallow import Schema, fields, post_load
from marshmallow.validate import OneOf
from thorn.models import *


def partial_schema_factory(schema_cls):
    schema = schema_cls(partial=True)
    for field_name, field in list(schema.fields.items()):
        if isinstance(field, fields.Nested):
            new_field = deepcopy(field)
            new_field.schema.partial = True
            schema.fields[field_name] = new_field
    return schema


def load_json(str_value):
    try:
        return json.loads(str_value)
    except BaseException:
        return "Error loading JSON"


# region Protected\s*
# endregion


class PermissionListResponseSchema(Schema):
    """ JSON serialization schema """
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    description = fields.String(required=True)
    applicable_to = fields.String(required=False, allow_none=True,
                                  validate=[OneOf(list(AssetType.__dict__.keys()))])
    enabled = fields.Boolean(required=True, default=True)

    # noinspection PyUnresolvedReferences
    @post_load
    def make_object(self, data):
        """ Deserialize data into an instance of Permission"""
        return Permission(**data)

    class Meta:
        ordered = True


class RoleListResponseSchema(Schema):
    """ JSON serialization schema """
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    description = fields.String(required=True)
    all_user = fields.Boolean(required=True, default=False)
    enabled = fields.Boolean(required=True, default=True)

    # noinspection PyUnresolvedReferences
    @post_load
    def make_object(self, data):
        """ Deserialize data into an instance of Role"""
        return Role(**data)

    class Meta:
        ordered = True


class UserListResponseSchema(Schema):
    """ JSON serialization schema """
    id = fields.Integer(required=True)
    email = fields.String(required=True)
    enabled = fields.Boolean(required=True, default=True)
    created_at = fields.DateTime(
        required=True,
        default=datetime.datetime.utcnow)
    updated_at = fields.DateTime(
        required=False,
        allow_none=True,
        missing=datetime.datetime.utcnow)
    first_name = fields.String(required=False, allow_none=True)
    last_name = fields.String(required=False, allow_none=True)
    locale = fields.String(required=False, allow_none=True)
    roles = fields.Nested(
        'thorn.schema.RoleListResponseSchema',
        required=True,
        many=True)

    # noinspection PyUnresolvedReferences
    @post_load
    def make_object(self, data):
        """ Deserialize data into an instance of User"""
        return User(**data)

    class Meta:
        ordered = True

