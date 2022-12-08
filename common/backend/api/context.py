from argparse import Namespace

from ariadne import (
    EnumType,
    MutationType,
    ObjectType,
    UnionType,
    QueryType,
    gql as GQL,
    make_executable_schema,
)

from common.api.gql.schema import Schema as gqlSchema
from common.api.gql.graphql_enum import GraphqlEnum as gqlEnum
from common.api.gql.graphql_input import InputType as gqlInputType
from common.api.gql.graphql_mutation_field import MutationField as gqlMutationField
from common.api.gql.graphql_query_field import QueryField as gqlQueryField
from common.api.gql.graphql_type import ObjectType as gqlObjectType
from common.api.gql.graphql_union_type import Union as gqlUnion

from common.api.constants import GraphQLEnumMapper

class Context:
    def __init__(
        self,
        engine=None,
        es=None,
        username=None,
        groups=None,
        cdkproxyurl=None,
    ):
        self.engine = engine
        self.es = es
        self.username = username
        self.groups = groups
        self.cdkproxyurl = cdkproxyurl


def bootstrap():
    classes = {
        gqlObjectType: [],
        gqlQueryField: [],
        gqlMutationField: [],
        gqlEnum: [],
        gqlUnion: [],
        gqlInputType: [],
    }

    Query = gqlObjectType(name='Query', fields=classes[gqlQueryField])

    Mutation = gqlObjectType(name='Mutation', fields=classes[gqlMutationField])

    for enumclass in GraphQLEnumMapper.__subclasses__():
        enumclass.toGraphQLEnum()

    for cls in classes.keys():
        for name in cls.class_instances['default'].keys():
            if cls.get_instance(name):
                classes[cls].append(cls.get_instance(name))
            else:
                raise Exception(f'Unknown Graphql Type :`{name}`')

    schema = gqlSchema(
        types=classes[gqlObjectType],
        inputs=classes[gqlInputType],
        enums=classes[gqlEnum],
        unions=classes[gqlUnion],
    )
    return schema


def save():
    schema = bootstrap()
    with open('schema.graphql', 'w') as f:
        f.write(schema.gql())


def resolver_adapter(resolver):
    def adapted(obj, info, **kwargs):
        response = resolver(
            context=Namespace(
                engine=info.context['engine'],
                es=info.context['es'],
                username=info.context['username'],
                groups=info.context['groups'],
                schema=info.context['schema'],
                cdkproxyurl=info.context['cdkproxyurl'],
            ),
            source=obj or None,
            **kwargs,
        )
        return response

    return adapted


def get_executable_schema():
    schema = bootstrap()
    _types = []
    for _type in schema.types:
        if _type.name == 'Query':
            query = QueryType()
            _types.append(query)
            for field in _type.fields:
                if field.resolver:
                    query.field(field.name)(resolver_adapter(field.resolver))
        elif _type.name == 'Mutation':
            mutation = MutationType()
            _types.append(mutation)
            for field in _type.fields:
                if field.resolver:
                    mutation.field(field.name)(resolver_adapter(field.resolver))
        else:
            object_type = ObjectType(name=_type.name)

            for field in _type.fields:
                if field.resolver:
                    object_type.field(field.name)(resolver_adapter(field.resolver))
            _types.append(object_type)

    _enums = []
    for enum in schema.enums:
        d = {}
        for k in enum.values:
            d[k.name] = k.value
        _enums.append(EnumType(enum.name, d))

    _unions = []
    for union in schema.unions:
        _unions.append(UnionType(union.name, union.resolver))

    type_defs = GQL(schema.gql(with_directives=False))
    executable_schema = make_executable_schema(type_defs, *(_types + _enums + _unions))
    return executable_schema
