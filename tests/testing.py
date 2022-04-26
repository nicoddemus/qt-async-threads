import threading


def assert_is_main_thread() -> None:
    """Assert that this function is being called from the main thread."""
    assert threading.current_thread() is threading.main_thread()


def assert_is_another_thread() -> None:
    """Assert that this function is being called from some thread other than main."""
    assert threading.current_thread() is not threading.main_thread()
