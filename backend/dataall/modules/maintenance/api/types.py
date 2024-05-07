"""Defines the object types of the Maintenance activity"""

from dataall.base.api import gql


Maintenance = gql.ObjectType(
    name='Maintenance', fields=[gql.NonNullableType(name='status', type=gql.String), gql.Field(name='mode', type=gql.String)]
)
