import os


def test_bozo_file_exists():
    assert os.path.exists("bozo.txt")
