import os


class DevSettings:
    @property
    def is_local_dev(self) -> bool:
        return os.environ.get("LOCAL_DEV")

    @property
    def is_under_test(self) -> bool:
        return "PYTEST_CURRENT_TEST" in os.environ


dev_settings = DevSettings()
