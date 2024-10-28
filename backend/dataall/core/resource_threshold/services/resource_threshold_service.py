from dataall.core.resource_threshold.db.resource_threshold_repositories import ResourceThresholdRepository
from dataall.base.db import exceptions
from functools import wraps
from dataall.base.config import config
from dataall.base.context import get_context

import logging

log = logging.getLogger(__name__)


class ResourceThresholdService:
    @staticmethod
    def check_invocation_count(action_type, max_count_config_path):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                context = get_context()
                with context.db_engine.scoped_session() as session:
                    count = ResourceThresholdRepository.get_count_today(
                        session=session, username=context.username, action_type=action_type
                    )
                    max_count = config.get_property(max_count_config_path, 10)
                    log.info(
                        f'User {context.username} has invoked {action_type} {count} times today of max {max_count}'
                    )
                    if count < max_count:
                        if count == 0:
                            ResourceThresholdRepository.add_entry(
                                session=session, username=context.username, action_type=action_type
                            )
                        else:
                            ResourceThresholdRepository.increment_count(
                                session=session, username=context.username, action_type=action_type
                            )
                        return func(*args, **kwargs)
                    else:
                        raise exceptions.ResourceThresholdExceeded(username=context.username, action=action_type)

            return wrapper

        return decorator
