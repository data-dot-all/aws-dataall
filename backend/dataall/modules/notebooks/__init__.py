"""Contains the code related to SageMaker notebooks"""
from dataall.db.api import TargetType
from dataall.modules.notebooks import gql, models, cdk, services, permissions

__all__ = ["gql", "models", "cdk", "services", "permissions"]

TargetType("notebook", permissions.GET_NOTEBOOK, permissions.UPDATE_NOTEBOOK)