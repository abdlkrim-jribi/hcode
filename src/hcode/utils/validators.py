

import re
from typing import Any, Callable, Iterable, List, Tuple


def is_email(value: str) -> bool:
    """Check if a string is a valid email address.

    Args:
        value (str): The string to validate.

    Returns:
        bool: True if the string matches an email pattern, False otherwise.
    """


    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, value) is not None


def is_url(value: str) -> bool:
    """Check if a string is a valid URL.

    Args:
        value (str): The string to validate.

    Returns:
        bool: True if the string matches a URL pattern, False otherwise.
    """


    pattern = (
        r"^(https?|ftp)://"
        r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
        r"[A-Z]{2,6}\b"
        r"(?:/?|/\S+)$"
    )
    return re.match(pattern, value, re.IGNORECASE) is not None


def is_positive_int(value: Any) -> bool:
    """Check if a value is a positive integer.

    Args:
        value (Any): The value to check.

    Returns:
        bool: True if `value` is an integer greater than zero, otherwise False.
    """


    return isinstance(value, int) and value > 0


def validate_collection(
    collection: Iterable,
    validator: Callable[[Any], bool],
) -> Tuple[bool, List[Any]]:
    """Validate each item in a collection using a provided validator.

    Args:
        collection (Iterable): The collection of items to validate.
        validator (Callable[[Any], bool]): A function that returns ``True`` for a valid item.

    Returns:
        Tuple[bool, List[Any]]: A tuple where the first element is ``True`` if all items are valid,
        and the second element is a list of the invalid items (empty if all are valid).
    """
    invalid_items = [item for item in collection if not validator(item)]
    return (len(invalid_items) == 0, invalid_items)
