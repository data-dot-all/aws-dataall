from typing import List, Callable, Dict
import logging

logger = logging.getLogger(__name__)

POLICY_LIMIT = 6144
POLICY_HEADERS_BUFFER = 144  # The policy headers take around 60 chars. An extra buffer of 84 chars is added for any additional spacing or char that is unaccounted.
MAXIMUM_NUMBER_MANAGED_POLICIES = 20  # Soft limit 10, hard limit 20


def split_policy_statements_in_chunks(statements: List[Dict]):
    """
    Splitter used for IAM policies with an undefined number of statements
    - Ensures that the size of the IAM policy remains below the POLICY LIMIT
    - If it exceeds the POLICY LIMIT, it breaks the policy into multiple policies (chunks)
    - Note the POLICY_HEADERS_BUFFER to account for the headers of the policy which usually take around ~60chars
    """
    chunks = []
    index = 0
    statements_list_of_strings = [str(s) for s in statements]
    total_length = len(', '.join(statements_list_of_strings))
    logger.info(f'Number of statements = {len(statements)}')
    logger.info(f'Total length of statements = {total_length}')
    max_length = max(statements_list_of_strings, key=len)
    if len(max_length) > POLICY_LIMIT - POLICY_HEADERS_BUFFER:
        raise Exception(f'Policy statement {max_length} exceeds maximum policy size')
    while index < len(statements):
        #  Iterating until all statements are assigned to a chunk.
        #  "index" represents the statement position in the statements list
        chunk = []
        chunk_size = 0
        while (
            index < len(statements) and chunk_size + len(str(statements[index])) < POLICY_LIMIT - POLICY_HEADERS_BUFFER
        ):
            #  Appends a statement to the chunk until we reach its maximum size.
            #  It compares, current size of the statements < allowed size for the statements section of a policy
            chunk.append(statements[index])
            chunk_size += len(str(statements[index]))
            index += 1
        chunks.append(chunk)
    logger.info(f'Total number of managed policies = {len(chunks)}')
    if len(chunks) > MAXIMUM_NUMBER_MANAGED_POLICIES:
        raise Exception('The number of policies calculated exceeds the allowed maximum number of managed policies')
    return chunks


def split_policy_with_resources_in_statements(base_sid: str, effect: str, actions: List[str], resources: List[str]):
    """
    The variable part of the policy is in the resources parameter of the PolicyStatement
    """

    def _build_statement(split, subset):
        return {'Sid': base_sid + str(split), 'Effect': effect, 'Action': actions, 'Resource': subset}

    total_length, base_length = _policy_analyzer(resources, _build_statement)
    extra_chars = len('" ," ')

    if total_length < POLICY_LIMIT - POLICY_HEADERS_BUFFER:
        logger.info('Not exceeding policy limit, returning statement ...')
        resulting_statement = _build_statement(1, resources)
        return [resulting_statement]
    else:
        logger.info('Exceeding policy limit, splitting statement ...')
        resulting_statements = _policy_splitter(
            base_length=base_length, resources=resources, extra_chars=extra_chars, statement_builder=_build_statement
        )
    return resulting_statements


def split_policy_with_mutiple_value_condition_in_statements(
    base_sid: str, effect: str, actions: List[str], resources: List[str], condition_dict: dict
):
    """
    The variable part of the policy is in the conditions parameter of the PolicyStatement
    conditions_dict passes the different components of the condition mapping
    """

    def _build_statement(split, subset):
        return {
            'Sid': base_sid + str(split),
            'Effect': effect,
            'Action': actions,
            'Resource': resources,
            'Condition': {condition_dict.get('key'): {condition_dict.get('resource'): subset}},
        }

    total_length, base_length = _policy_analyzer(condition_dict.get('values'), _build_statement)
    extra_chars = len(
        str(f'"Condition":  {{ "{condition_dict.get("key")}": {{"{condition_dict.get("resource")}": }} }}')
    )

    if total_length < POLICY_LIMIT - POLICY_HEADERS_BUFFER:
        logger.info('Not exceeding policy limit, returning statement ...')
        resulting_statement = _build_statement(1, condition_dict.get('values'))
        return [resulting_statement]
    else:
        logger.info('Exceeding policy limit, splitting values ...')
        resulting_statements = _policy_splitter(
            base_length=base_length,
            resources=condition_dict.get('values'),
            extra_chars=extra_chars,
            statement_builder=_build_statement,
        )

    return resulting_statements


def _policy_analyzer(resources: List[str], statement_builder: Callable[[int, List[str]], Dict]):
    """
    Calculates the policy size with the resources (total_length) and without resources (base_length)
    """
    statement_without_resources = statement_builder(1, ['*'])
    resources_str = '" ," '.join(r for r in resources)
    base_length = len(str(statement_without_resources))
    total_length = base_length + len(resources_str)
    logger.info(f'Policy base length = {base_length}')
    logger.info(f'Resources as string length = {len(resources_str)}')
    logger.info(f'Total length approximated as base length + resources string length = {total_length}')

    return total_length, base_length


def _policy_splitter(
    base_length: int,
    resources: List[str],
    extra_chars: int,
    statement_builder: Callable[[int, List[str]], Dict],
):
    """
    Splitter used for IAM policy statements with an undefined number of resources one of the parameters of the policy.
    - Ensures that the size of the IAM statement is below the POLICY LIMIT
    - If it exceeds the POLICY LIMIT, it breaks the statement in multiple statements with a subset of resources
    - Note the POLICY_HEADERS_BUFFER to account for the headers of the policy which usually take around ~60chars
    """
    index = 0
    split = 0
    resulting_statements = []
    while index < len(resources):
        #  Iterating until all values are defined in a policy statement.
        #  "index" represents the position of the value in the values list
        size = 0
        subset = []
        while (
            index < len(resources)
            and (size + len(resources[index]) + extra_chars) < POLICY_LIMIT - POLICY_HEADERS_BUFFER - base_length
        ):
            #  Appending a resource to the subset list until we reach the maximum size for the condition section
            #  It compares: current size of subset versus the allowed size of the condition section in a statement
            subset.append(resources[index])
            size += len(resources[index]) + extra_chars
            index += 1
        resulting_statement = statement_builder(split=split, subset=subset)
        split += 1
        resulting_statements.append(resulting_statement)
    logger.info(f'Statement divided into {split + 1} smaller statements')
    return resulting_statements
