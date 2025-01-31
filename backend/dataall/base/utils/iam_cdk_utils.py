from typing import Dict, Any, List
from aws_cdk import aws_iam as iam

from dataall.base.utils.iam_policy_utils import (
    split_policy_statements_in_chunks,
    split_policy_with_resources_in_statements,
    split_policy_with_mutiple_value_condition_in_statements,
)


def convert_from_json_to_iam_policy_statement_with_conditions(iam_policy: Dict[Any, Any]):
    return iam.PolicyStatement(
        sid=iam_policy.get('Sid'),
        effect=iam.Effect.ALLOW if iam_policy.get('Effect').casefold() == 'Allow'.casefold() else iam.Effect.DENY,
        actions=_convert_to_array(str, iam_policy.get('Action')),
        resources=_convert_to_array(str, iam_policy.get('Resource')),
        conditions=iam_policy.get('Condition'),
    )


def convert_from_json_to_iam_policy_statement_with_resources(iam_policy: Dict[Any, Any]):
    return iam.PolicyStatement(
        sid=iam_policy.get('Sid'),
        effect=iam.Effect.ALLOW if iam_policy.get('Effect').casefold() == 'Allow'.casefold() else iam.Effect.DENY,
        actions=_convert_to_array(str, iam_policy.get('Action')),
        resources=_convert_to_array(str, iam_policy.get('Resource')),
    )


def process_and_split_statements_in_chunks(statements: List[Dict]):
    statement_chunks_json: List[List[Dict]] = split_policy_statements_in_chunks(statements)
    statements_chunks: List[List[iam.PolicyStatement]] = []
    for statement_js_chunk in statement_chunks_json:
        statements: List[iam.PolicyStatement] = []
        for statement in statement_js_chunk:
            if statement.get('Condition', None):
                statements.append(convert_from_json_to_iam_policy_statement_with_conditions(statement))
            else:
                statements.append(convert_from_json_to_iam_policy_statement_with_resources(statement))
        statements_chunks.append(statements)
    return statements_chunks


def process_and_split_policy_with_conditions_in_statements(
    base_sid: str, effect: str, actions: List[str], resources: List[str], condition_dict: Dict = None
):
    json_statements = split_policy_with_mutiple_value_condition_in_statements(
        base_sid=base_sid, effect=effect, actions=actions, resources=resources, condition_dict=condition_dict
    )

    iam_statements: [iam.PolicyStatement] = []
    for json_statement in json_statements:
        iam_policy_statement = convert_from_json_to_iam_policy_statement_with_conditions(json_statement)
        iam_statements.append(iam_policy_statement)
    return iam_statements


def process_and_split_policy_with_resources_in_statements(
    base_sid: str, effect: str, actions: List[str], resources: List[str]
):
    json_statements = split_policy_with_resources_in_statements(
        base_sid=base_sid, effect=effect, actions=actions, resources=resources
    )
    iam_statements: [iam.PolicyStatement] = []
    for json_statement in json_statements:
        iam_policy_statement = convert_from_json_to_iam_policy_statement_with_resources(json_statement)
        iam_statements.append(iam_policy_statement)
    return iam_statements


# If item is of item type i.e. single instance if present, then wrap in an array.
# This is helpful at places where array is required even if one element is present
def _convert_to_array(item_type, item):
    if isinstance(item, item_type):
        return [item]
    return item
