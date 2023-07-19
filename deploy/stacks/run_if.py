from .deploy_config import deploy_config


def _process_func(func):
    """Helper function that helps decorate methods/functions"""
    def no_decorated(f):
        return f

    static_func = False
    try:
        fn = func.__func__
        static_func = True
    except AttributeError:
        fn = func

    # returns a function to call and static decorator if applied
    return fn, staticmethod if static_func else no_decorated


def run_if(active_property: str):
    """
    Decorator that check whether a method should be active or not.
    The active_property must be a boolean value in the config file
    """
    def decorator(f):
        fn, fn_decorator = _process_func(f)

        def decorated(*args, **kwargs):
            is_active = deploy_config.get_property(active_property, False)
            if not is_active:
                return None

            return fn(*args, **kwargs)

        return fn_decorator(decorated)

    return decorator
