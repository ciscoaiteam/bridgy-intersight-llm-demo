import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



# Create a class-based decorator
class ExecutionTimer:
    def __init__(self, logger=None):
        """
        Initialize the decorator with an optional logger.
        :param logger: A logger instance for logging execution times.
        """
        self.logger = logger or logging.getLogger(__name__)

    def __call__(self, func):
        """
        Make the class instance callable, so it acts as a decorator.
        :param func: The function to be wrapped.
        """
        @wraps(func)  # Preserve original function metadata
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)  # Support for async functions
            end_time = time.time()
            execution_time = end_time - start_time
            self.logger.debug(
                f"Function '{func.__name__}' executed in {execution_time:.4f} seconds"
            )
            return result

        return wrapper