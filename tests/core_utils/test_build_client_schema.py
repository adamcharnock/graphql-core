from collections import OrderedDict
from pytest import raises
from graphql.core import graphql
from graphql.core.error import format_error
from graphql.core.type import (
    GraphQLSchema,
    GraphQLArgument,
    GraphQLScalarType,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLUnionType,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLField,
    GraphQLInputObjectType,
    GraphQLInputObjectField,
    GraphQLList,
    GraphQLNonNull,
    GraphQLInt,
    GraphQLFloat,
    GraphQLString,
    GraphQLBoolean,
    GraphQLID,
)
from graphql.core.utils.introspection_query import introspection_query
from graphql.core.utils.build_client_schema import build_client_schema


def _test_schema(server_schema):
    initial_introspection = graphql(server_schema, introspection_query)
    client_schema = build_client_schema(initial_introspection.data)
    second_introspection = graphql(client_schema, introspection_query)
    assert initial_introspection.data == second_introspection.data

    return client_schema


def test_it_builds_a_simple_schema():
    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='Simple',
            description='This is a simple type',
            fields={
                'string': GraphQLField(GraphQLString, description='This is a string field')
            }
        )
    )
    _test_schema(schema)


def test_builds_a_simple_schema_with_a_mutation_type():
    QueryType = GraphQLObjectType(
        name='QueryType',
        description='This is a simple query type',
        fields={
            'string': GraphQLField(GraphQLString, description='This is a string field.')
        }
    )
    MutationType = GraphQLObjectType(
        name='MutationType',
        description='This is a simple mutation type',
        fields={
            'setString': GraphQLField(GraphQLString, description='Set the string field', args={
                'value': GraphQLArgument(GraphQLString)
            })
        }
    )

    schema = GraphQLSchema(QueryType, MutationType)
    _test_schema(schema)


def test_uses_built_in_scalars_when_possible():
    customScalar = GraphQLScalarType(
        name='CustomScalar',
        serialize=lambda: None
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='Scalars',
            fields=OrderedDict([
                ('int', GraphQLField(GraphQLInt)),
                ('float', GraphQLField(GraphQLFloat)),
                ('string', GraphQLField(GraphQLString)),
                ('boolean', GraphQLField(GraphQLBoolean)),
                ('id', GraphQLField(GraphQLID)),
                ('custom', GraphQLField(customScalar)),
            ])
        )
    )

    client_schema = _test_schema(schema)

    assert client_schema.get_type('Int') == GraphQLInt
    assert client_schema.get_type('Float') == GraphQLFloat
    assert client_schema.get_type('String') == GraphQLString
    assert client_schema.get_type('Boolean') == GraphQLBoolean
    assert client_schema.get_type('ID') == GraphQLID

    assert client_schema.get_type('CustomScalar') != customScalar


def test_builds_a_schema_with_a_recursive_type_reference():
    recurType = GraphQLObjectType(
        name='Recur',
        fields=lambda: {
            'recur': GraphQLField(recurType)
        }
    )

    schema = GraphQLSchema(query=recurType)
    _test_schema(schema)


def test_builds_a_schema_with_a_circular_type_reference():
    DogType = GraphQLObjectType(
        name='Dog',
        fields=lambda: {
            'bestFriend': GraphQLField(HumanType)
        }
    )

    HumanType = GraphQLObjectType(
        name='Human',
        fields=lambda: {
            'bestFriend': GraphQLField(DogType)
        }
    )

    schema = GraphQLSchema(query=GraphQLObjectType(
        name='Circular',
        fields=OrderedDict([
            ('dog', GraphQLField(DogType)),
            ('human', GraphQLField(HumanType)),
        ])
    ))

    _test_schema(schema)


def test_builds_a_schema_with_an_interface():
    FriendlyType = GraphQLInterfaceType(
        name='Friendly',
        resolve_type=lambda: None,
        fields=lambda: {
            'bestFriend': GraphQLField(FriendlyType, description='The best friend of this friendly thing.')
        }
    )

    GraphQLObjectType(
        name='Human',
        interfaces=[FriendlyType],
        fields=lambda: {
            'bestFriend': GraphQLField(FriendlyType)
        }
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='WithInterface',
            fields={
                'friendly': GraphQLField(FriendlyType)
            }
        )
    )

    _test_schema(schema)


def test_builds_a_schema_with_a_union():
    DogType = GraphQLObjectType(
        name='Dog',
        fields=lambda: {
            'bestFriend': GraphQLField(FriendlyType)
        }
    )

    HumanType = GraphQLObjectType(
        name='Human',
        fields=lambda: {
            'bestFriend': GraphQLField(FriendlyType)
        }
    )

    FriendlyType = GraphQLUnionType(
        name='Friendly',
        resolve_type=lambda: None,
        types=[DogType, HumanType]
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='WithUnion',
            fields={
                'friendly': GraphQLField(FriendlyType)
            }
        )
    )

    _test_schema(schema)


def test_builds_a_schema_with_complex_field_values():
    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='ComplexFields',
            fields=OrderedDict([
                ('string', GraphQLField(GraphQLString)),
                ('listOfString', GraphQLField(GraphQLList(GraphQLString))),
                ('nonNullString', GraphQLField(GraphQLNonNull(GraphQLString))),
                ('nonNullListOfString', GraphQLField(GraphQLNonNull(GraphQLList(GraphQLString)))),
                ('nonNullListOfNonNullString', GraphQLField(
                    GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLString)))
                ))
            ])
        )
    )

    _test_schema(schema)


def test_builds_a_schema_with_field_arguments():
    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='ArgFields',
            fields=OrderedDict([
                ('one', GraphQLField(GraphQLString, description='A field with a single arg', args={
                    'intArg': GraphQLArgument(GraphQLInt, description='This is an int arg')
                })),
                ('two', GraphQLField(GraphQLString, description='A field with two args', args=OrderedDict([
                    ('listArg', GraphQLArgument(
                        GraphQLList(GraphQLInt),
                        description='This is a list of int arg'
                    )),
                    ('requiredArg', GraphQLArgument(
                        GraphQLNonNull(GraphQLBoolean),
                        description='This is a required arg'
                    ))
                ]))),
            ])
        )
    )

    _test_schema(schema)


def test_builds_a_schema_with_an_enum():
    FoodEnum = GraphQLEnumType(
        name='Food',
        description='Varieties of food stuffs',
        values=OrderedDict([
            ('VEGETABLES', GraphQLEnumValue(1, description='Foods that are vegetables.')),
            ('FRUITS', GraphQLEnumValue(2, description='Foods that are fruits.')),
            ('OILS', GraphQLEnumValue(3, description='Foods that are oils.')),
            ('DAIRY', GraphQLEnumValue(4, description='Foods that are dairy.')),
            ('MEAT', GraphQLEnumValue(5, description='Foods that are meat.')),
        ])
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='EnumFields',
            fields={
                'food': GraphQLField(
                    FoodEnum,
                    description='Repeats the arg you give it',
                    args={
                        'kind': GraphQLArgument(
                            FoodEnum,
                            description='what kind of food?'
                        )
                    }
                )
            }
        )
    )

    client_schema = _test_schema(schema)
    clientFoodEnum = client_schema.get_type('Food')
    assert isinstance(clientFoodEnum, GraphQLEnumType)

    assert clientFoodEnum.get_values() == [
        GraphQLEnumValue(name='VEGETABLES', value='VEGETABLES', description='Foods that are vegetables.'),
        GraphQLEnumValue(name='FRUITS', value='FRUITS', description='Foods that are fruits.'),
        GraphQLEnumValue(name='OILS', value='OILS', description='Foods that are oils.'),
        GraphQLEnumValue(name='DAIRY', value='DAIRY', description='Foods that are dairy.'),
        GraphQLEnumValue(name='MEAT', value='MEAT', description='Foods that are meat.')
    ]


def test_builds_a_schema_with_an_input_object():
    AddressType = GraphQLInputObjectType(
        name='Address',
        description='An input address',
        fields=OrderedDict([
            ('street',
             GraphQLInputObjectField(GraphQLNonNull(GraphQLString), description='What street is this address?')),
            ('city',
             GraphQLInputObjectField(GraphQLNonNull(GraphQLString), description='The city the address is within?')),
            ('country', GraphQLInputObjectField(GraphQLString, description='The country (blank will assume USA).',
                                                default_value='USA')),
        ])
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='HasInputObjectFields',
            fields={
                'geocode': GraphQLField(
                    description='Get a geocode from an address',
                    type=GraphQLString,
                    args={
                        'address': GraphQLArgument(
                            description='The address to lookup',
                            type=AddressType
                        )
                    }
                )
            }
        )
    )

    _test_schema(schema)


def test_builds_a_schema_with_field_arguments_with_default_values():
    GeoType = GraphQLInputObjectType(
        name='Geo',
        fields=OrderedDict([
            ('lat', GraphQLInputObjectField(GraphQLFloat)),
            ('lon', GraphQLInputObjectField(GraphQLFloat)),
        ])
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='ArgFields',
            fields=OrderedDict([
                ('defaultInt', GraphQLField(
                    GraphQLString,
                    args={
                        'intArg': GraphQLArgument(
                            GraphQLInt,
                            default_value=10
                        )
                    }
                )),
                ('defaultList', GraphQLField(
                    GraphQLString,
                    args={
                        'listArg': GraphQLArgument(
                            GraphQLList(GraphQLInt),
                            default_value=[1, 2, 3]
                        )
                    }
                )),
                ('defaultObject', GraphQLField(
                    GraphQLString,
                    args={
                        'objArg': GraphQLArgument(
                            GeoType,
                            default_value={'lat': 37.485, 'lon': -122.148}
                        )
                    }
                ))
            ])
        )
    )

    _test_schema(schema)


def test_cannot_use_client_schema_for_general_execution():
    customScalar = GraphQLScalarType(
        name='CustomScalar',
        serialize=lambda: None
    )

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='Query',
            fields={
                'foo': GraphQLField(
                    GraphQLString,
                    args=OrderedDict([
                        ('custom1', GraphQLArgument(customScalar)),
                        ('custom2', GraphQLArgument(customScalar))
                    ])
                )
            }
        )
    )

    introspection = graphql(schema, introspection_query)
    client_schema = build_client_schema(introspection.data)

    class data:
        foo = 'bar'

    result = graphql(
        client_schema,
        'query NoNo($v: CustomScalar) { foo(custom1: 123, custom2: $v) }',
        data,
        {'v': 'baz'}
    )

    assert result.data == {'foo': None}
    assert [format_error(e) for e in result.errors] == [
        {'locations': [{'column': 32, 'line': 1}], 'message': 'Client Schema cannot be used for execution.'}
    ]


def test_throws_when_given_empty_types():
    incomplete_introspection = {
        '__schema': {
            'queryType': {'name': 'QueryType'},
            'types': []
        }
    }

    with raises(Exception) as excinfo:
        build_client_schema(incomplete_introspection)

    assert str(excinfo.value) == 'Invalid or incomplete schema, unknown type: QueryType. Ensure that a full ' \
                                 'introspection query is used in order to build a client schema.'


def test_throws_when_missing_kind():
    incomplete_introspection = {
        '__schema': {
            'queryType': {'name': 'QueryType'},
            'types': [{
                'name': 'QueryType'
            }]
        }
    }

    with raises(Exception) as excinfo:
        build_client_schema(incomplete_introspection)

    assert str(excinfo.value) == 'Invalid or incomplete schema, unknown kind: None. Ensure that a full ' \
                                 'introspection query is used in order to build a client schema.'


def test_fails_on_very_deep_lists():
    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='Query',
            fields={
                'foo': GraphQLField(
                    GraphQLList(GraphQLList(GraphQLList(GraphQLList(GraphQLString))))
                )
            }
        )
    )

    introspection = graphql(schema, introspection_query)

    with raises(Exception) as excinfo:
        build_client_schema(introspection.data)

    assert str(excinfo.value) == 'Decorated type deeper than introspection query.'


def test_fails_on_a_deep_non_null():
    schema = GraphQLSchema(
        query=GraphQLObjectType(
            name='Query',
            fields={
                'foo': GraphQLField(
                    GraphQLList(GraphQLList(GraphQLList(GraphQLNonNull(GraphQLString))))
                )
            }
        )
    )

    introspection = graphql(schema, introspection_query)

    with raises(Exception) as excinfo:
        build_client_schema(introspection.data)

    assert str(excinfo.value) == 'Decorated type deeper than introspection query.'
