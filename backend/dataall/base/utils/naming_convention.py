from enum import Enum
import re
from .slugify import slugify


class NamingConventionPattern(Enum):
    S3 = {
        'regex': '[^a-zA-Z0-9-]',
        'separator': '-',
        'max_length': 63,
        'valid_external_regex': '(?!(^xn--|.+-s3alias$))^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$',
    }
    KMS = {'regex': '[^a-zA-Z0-9-]$', 'separator': '-', 'max_length': 63, 'valid_external_regex': '^[a-zA-Z0-9_-]+$'}
    IAM = {'regex': '[^a-zA-Z0-9-_]', 'separator': '-', 'max_length': 63}  # Role names up to 64 chars
    IAM_POLICY = {'regex': '[^a-zA-Z0-9-_]', 'separator': '-', 'max_length': 128}  # Policy names up to 128 chars
    GLUE = {
        'regex': '[^a-zA-Z0-9_]',
        'separator': '_',
        'max_length': 240,
        'valid_external_regex': '^[a-zA-Z0-9_]+$',
    }  # Limit 255 - 15 extra chars buffer
    GLUE_ETL = {'regex': '[^a-zA-Z0-9-]', 'separator': '-', 'max_length': 52}
    NOTEBOOK = {'regex': '[^a-zA-Z0-9-]', 'separator': '-', 'max_length': 63}
    MLSTUDIO_DOMAIN = {'regex': '[^a-zA-Z0-9-]', 'separator': '-', 'max_length': 63}
    DEFAULT = {'regex': '[^a-zA-Z0-9-_]', 'separator': '-', 'max_length': 63}
    DEFAULT_SEARCH = {'regex': '[^a-zA-Z0-9-_:. ]'}
    OPENSEARCH = {'regex': '[^a-z0-9-]', 'separator': '-', 'max_length': 27}
    OPENSEARCH_SERVERLESS = {'regex': '[^a-z0-9-]', 'separator': '-', 'max_length': 31}
    DATA_FILTERS = {'regex': '[^a-z0-9_]', 'separator': '_', 'max_length': 31}
    REDSHIFT_DATASHARE = {
        'regex': '[^a-zA-Z0-9_]',
        'separator': '_',
        'max_length': 1000,
    }  # Maximum length of 2147483647


class NamingConventionService:
    def __init__(
        self,
        target_label: str,
        pattern: NamingConventionPattern,
        target_uri: str = '',
        resource_prefix: str = '',
    ):
        self.target_label = target_label
        self.target_uri = target_uri if target_uri else ''
        self.service = pattern.name
        self.resource_prefix = resource_prefix

    def build_compliant_name(self) -> str:
        """
        Builds a compliant AWS resource name
        """
        regex = NamingConventionPattern[self.service].value['regex']
        separator = NamingConventionPattern[self.service].value['separator']
        max_length = NamingConventionPattern[self.service].value['max_length']
        suffix = f'-{self.target_uri}' if len(self.target_uri) else ''
        return f'{slugify(self.resource_prefix + "-" + self.target_label[: (max_length - len(self.resource_prefix + self.target_uri))] + suffix, regex_pattern=rf"{regex}", separator=separator, lowercase=True)}'

    def build_compliant_name_with_index(self, index: int = None) -> str:
        """
        Builds a compliant AWS resource name with an index at the end of the policy name
        IMP - If no index is provided, then this method provides a base policy name without index. Base policy name is calculated by considering the length of string required for index
        This is done so that the base policy name doesn't change when an index is added to the string.
        """
        regex = NamingConventionPattern[self.service].value['regex']
        separator = NamingConventionPattern[self.service].value['separator']
        max_length = NamingConventionPattern[self.service].value['max_length']
        index_string_length = 2  # This is added to adjust the target label string even if the index is set to None. This helps in getting the base policy name when index is None
        index_string = f'-{index}' if index is not None else ''
        suffix = f'-{self.target_uri}' if len(self.target_uri) else ''
        return f'{slugify(self.resource_prefix + "-" + self.target_label[: (max_length - len(self.resource_prefix + self.target_uri) - index_string_length)] + suffix + index_string, regex_pattern=rf"{regex}", separator=separator, lowercase=True)}'

    def validate_name(self):
        regex = NamingConventionPattern[self.service].value['regex']
        max_length = NamingConventionPattern[self.service].value['max_length']
        if re.search(regex, self.target_label):
            raise Exception(
                f'An error occurred (InvalidInput): label value {self.target_label} must match the pattern {regex}'
            )
        elif len(self.target_label) > max_length:
            raise Exception(
                f'An error occurred (InvalidInput): label value {self.target_label} must be less than {max_length} characters'
            )

    def sanitize(self):
        regex = NamingConventionPattern[self.service].value['regex']
        return re.sub(regex, '', self.target_label)

    def validate_imported_name(self):
        max_length = NamingConventionPattern[self.service].value['max_length']
        valid_external_regex = NamingConventionPattern[self.service].value.get('valid_external_regex', '.*')
        if 'arn:aws:' in self.target_label:
            raise Exception('An error occurred (InvalidInput): name expected, arn-like string received')
        if not re.search(valid_external_regex, self.target_label):
            raise Exception(
                f'An error occurred (InvalidInput): label value {self.target_label} must match the pattern {valid_external_regex}'
            )
        elif len(self.target_label) > max_length:
            raise Exception(
                f'An error occurred (InvalidInput): label value {self.target_label} must be less than {max_length} characters'
            )
