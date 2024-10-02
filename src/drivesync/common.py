import random
import string
import tempfile
import pathlib

class Common:
    @staticmethod
    def setup():
        Common.temp_dir = tempfile.TemporaryDirectory()

    @staticmethod
    def teardown():
        Common.temp_dir.cleanup()

    @staticmethod
    def get_temp_file(extension=None):
        name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return pathlib.Path(Common.temp_dir.name, f"{name}.{extension}" if extension is not None else name)
    