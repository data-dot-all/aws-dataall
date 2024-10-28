class ObjectNotFound(Exception):
    def __init__(self, type, id):
        self.type = type
        self.id = id
        self.message = self.message = f"""
            An error occurred (ResourceNotFound):
            Resource {self.type} with URI {self.id} not found
        """

    def __str__(self):
        return f'{self.message}'


class TenantUnauthorized(Exception):
    def __init__(self, username, action, tenant_name):
        self.action = action
        self.username = username
        self.message = f"""
            An error occurred (UnauthorizedOperation) when calling {self.action} operation:
            User: {self.username} is not authorized to perform: {self.action} on {tenant_name}.
        """

    def __str__(self):
        return self.message


class ResourceUnauthorized(Exception):
    def __init__(self, username, action, resource_uri):
        self.action = action
        self.username = username
        self.resource_uri = resource_uri
        self.message = f"""
            An error occurred (UnauthorizedOperation) when calling {self.action} operation:
            User: {self.username} is not authorized to perform: {self.action} on resource: {resource_uri}
        """

    def __str__(self):
        return self.message


class RequiredParameter(Exception):
    def __init__(self, param_name):
        self.param_name = param_name
        self.message = f'An error occurred (RequiredParameter): {param_name} is required'

    def __str__(self):
        return f'{self.message}'


class InvalidInput(Exception):
    def __init__(self, param_name, param_value, constraint):
        self.param_name = param_name
        self.param_value = param_value
        self.message = f"""
                    An error occurred (InvalidInput): '{param_name} value {param_value} must be {constraint}'
        """

    def __str__(self):
        return f'{self.message}'


class PermissionUnauthorized(Exception):
    def __init__(self, action, group_name, resource_uri):
        self.group_name = group_name
        self.action = action
        self.resource_uri = resource_uri
        self.message = self.message = f"""
            An error occurred (UnauthorizedOperation) when calling {self.action} operation:
            Invalid permissions can not be granted to group {group_name} on resource: {resource_uri}
        """

    def __str__(self):
        return f'{self.message}'


class TenantPermissionUnauthorized(Exception):
    def __init__(self, action, group_name, tenant_name):
        self.group_name = group_name
        self.action = action
        self.tenant_name = tenant_name
        self.message = self.message = f"""
            An error occurred (UnauthorizedOperation) when calling {self.action} operation:
            Invalid permissions can not be granted to group {group_name} on tenant: {tenant_name}
        """

    def __str__(self):
        return f'{self.message}'


class UnauthorizedOperation(Exception):
    def __init__(self, action, message):
        self.action = action
        self.message = f"""
            An error occurred (UnauthorizedOperation) when calling {self.action} operation:
            {message}
        """

    def __str__(self):
        return f'{self.message}'


class ResourceAlreadyExists(Exception):
    def __init__(self, action, message):
        self.action = action
        self.message = f"""
                    An error occurred (ResourceAlreadyExists) when calling {self.action} operation:
                    {message}
                """

    def __str__(self):
        return f'{self.message}'


class ResourceShared(Exception):
    def __init__(self, action, message):
        self.action = action
        self.message = f"""
                    An error occurred (ResourceShared) when calling {self.action} operation:
                    {message}
                """

    def __str__(self):
        return f'{self.message}'


class AWSResourceNotFound(Exception):
    def __init__(self, action, message):
        self.action = action
        self.message = f"""
                    An error occurred (AWSResourceNotFound) when calling {self.action} operation:
                    {message}
                """

    def __str__(self):
        return f'{self.message}'


class AWSResourceNotAvailable(Exception):
    def __init__(self, action, message):
        self.action = action
        self.message = f"""
                    An error occurred (AWSResourceNotAvailable) when calling {self.action} operation:
                    {message}
                """

    def __str__(self):
        return f'{self.message}'


class EnvironmentResourcesFound(Exception):
    def __init__(self, action, message):
        self.action = action
        self.message = f"""
                    An error occurred (EnvironmentResourcesFound) when calling {self.action} operation:
                    {message}
                """

    def __str__(self):
        return f'{self.message}'


class OrganizationResourcesFound(Exception):
    def __init__(self, action, message):
        self.action = action
        self.message = f"""
                    An error occurred (OrganizationResourcesFound) when calling {self.action} operation:
                    {message}
                """

    def __str__(self):
        return f'{self.message}'


class ResourceLockTimeout(Exception):
    def __init__(self, action, message):
        self.action = action
        self.message = f"""
                    An error occurred (ResourceLockTimeout) when calling {self.action} operation:
                    {message}
                """

    def __str__(self):
        return f'{self.message}'


class ResourceThresholdExceeded(Exception):
    def __init__(self, username, action):
        self.username = username
        self.action = action
        self.message = f"""
                    An error occurred (ResourceThresholdExceeded) when calling {self.action} operation:
                    Requests exceeded max daily invocation count for User: {self.username}
                """

    def __str__(self):
        return f'{self.message}'


class ModelGuardrailException(Exception):
    def __init__(self, message):
        self.message = f"""
                    An error occurred (ModelGuardrailException) when invoking the model: {message}
                """

    def __str__(self):
        return f'{self.message}'
