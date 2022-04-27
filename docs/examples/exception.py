import sys
import traceback


def install_except_hook() -> None:
    def excepthook(exc_type: object, exc_value: BaseException, exc_tb: object) -> None:
        traceback.print_exception(exc_value)

    sys.excepthook = excepthook
