#
# This is a an integration testing framework that can be used to check your
# implementation against some of the typical scenarios. You don't have to
# implement your solution in Python, but nevertheless you're encouraged to use
# this framework to prove your solution works as expected. In order to do that,
# your solution has to be comparible with this framework in two aspects:
# 1. command-line arguments -- framework should be able to pass arguments to
#   your implementation and run it
# 2. client side file structure should mirror server side file structure
# The framework contains a simple and inefficient implementation. It's given
# for reference purposes only to demonstrate how to run the framework and that
# it's possible to pass all the tests.
#
# Install dependencies:
# pip3 install --user pytest
#
# How to run:
# mkdir -p /tmp/dropbox/client
# mkdir -p /tmp/dropbox/server


# RUN own client and server version:
# export CLIENT_CMD='python3 -c "import client as client; client.client()" {port} {path}'
# export SERVER_CMD='python3 -c "import server as server; server.server()" {port} {path}'
#

# Verbose, with stdout, filter by test name
# pytest -vv -s . -k 'test_some_name'
# Quiet, show summary in the end
# pytest -q -rapP
# Verbose, with stdout, show summary in the end
# pytest -s -vv -q -rapP
#
from contextlib import closing
from hashlib import md5
from os import environ, getpgid, killpg, mkdir, remove, setsid, walk, listdir, unlink, rename, rmdir
from os.path import exists, getsize, isfile, join, sep, islink, isdir
from shutil import rmtree, move
from signal import SIGKILL, SIGTERM
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from subprocess import Popen, TimeoutExpired
from sys import stderr, stdout
from time import sleep
from unittest import TestCase


ASSERT_TIMEOUT = 20.0
ASSERT_STEP = 1.0
SHUTDOWN_TIMEOUT = 15.0

SERVER_PATH = "/tmp/dropbox/server"
CLIENT_PATH = "/tmp/dropbox/client"

def create(filename, data):
    """Save data into the given filename."""
    with open(filename, "w") as file_:
        file_.write(data)

def find_free_port():
    """ Find free port to use"""
    with closing(socket(AF_INET, SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        return s.getsockname()[1]

def reset_path(path):
    """Remove whole directory and add back again"""
    if exists(path):
        rmtree(path)
    mkdir(path)

def wipe_path(path):
    """ Similar to reset_path, but walks through the directory and removes each file/dir individually.
        Mostly for test purposes"""
    for filename in listdir(path):
        full = join(path, filename)
        if isfile(full) or islink(full):
            unlink(full)
        elif isdir(full):
            rmtree(full)

def path_content_to_string(path):
    """ Convert contents of a directory recursively into a string for easier comparison,
        content is also changed into a hash """
    lines = []
    prefix_len = len(path + sep)
    for root, dirs, files in walk(path):
        for dir_ in dirs:
            full_path = join(root, dir_)
            relative_path = full_path[prefix_len:]
            size = 0
            type_ = "dir"
            hash_ = "0"
            line = "{},{},{},{}".format(relative_path, type_, size, hash_)
            lines.append(line)

        for filename in files:
            full_path = join(root, filename)
            relative_path = full_path[prefix_len:]
            size = getsize(full_path)
            type_ = "file" if isfile(full_path) else "dir"
            hash_ = get_md5(full_path)
            line = "{},{},{},{}".format(relative_path, type_, size, hash_)
            lines.append(line)

    lines = sorted(lines)
    return "\n".join(lines)

def get_md5(filename):
    # Returns md5 hash of a file or 0 if filename is not a path to a file
    if not isfile(filename):
        return "0"
    hash_md5 = md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def assert_paths_in_sync(path1, path2, timeout=ASSERT_TIMEOUT, step=ASSERT_STEP):
    # Tests if both path1 and path2 contain the same data and structure
    current_time = 0
    assert current_time < timeout, "we should always go around the loop at least once"
    while current_time < timeout:
        contents1 = path_content_to_string(path1)
        contents2 = path_content_to_string(path2)
        if contents1 == contents2:
            return
        sleep(step)
        current_time += step
    assert contents1 == contents2


class Process:
    def __init__(self, cmd_line):
        print("Starting ", cmd_line)

        self._process = Popen(
            cmd_line, shell=True, preexec_fn=setsid, stdout=stdout, stderr=stderr
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.shutdown()

    def shutdown(self):
        killpg(getpgid(self._process.pid), SIGTERM)
        try:
            self._process.wait(SHUTDOWN_TIMEOUT)
        except TimeoutExpired:
            killpg(getpgid(self._process.pid), SIGKILL)
        sleep(2.0)

class TestClassObserverSync(TestCase):
    def setUp(self):
        self.spath = SERVER_PATH
        self.cpath = CLIENT_PATH
        
        reset_path(self.spath)
        reset_path(self.cpath)
        port = find_free_port()
        self.server_cmd = environ["SERVER_CMD"].format(port=port, path=self.spath)
        self.client_cmd = environ["CLIENT_CMD"].format(port=port, path=self.cpath)
        self.server_process = Process(self.server_cmd)
        sleep(1.0)
        self.client_process = Process(self.client_cmd)
        sleep(1.0)
        assert_paths_in_sync(self.cpath, self.spath)
        print("DONE WITH SETUP")

    def tearDown(self):
        self.server_process.shutdown()
        self.client_process.shutdown()

    def test_move_folder_outside(self):
        mkdir(join(self.cpath, "newemptydir"))
        assert_paths_in_sync(self.cpath, self.spath)
        move(join(self.cpath, "newemptydir"), "/home/markb/Documents/Program_repos/Fileserver/test")
        assert_paths_in_sync(self.cpath, self.spath)
        rmdir("/home/markb/Documents/Program_repos/Fileserver/test")

    def test_move_file_outside(self):
        create(join(self.cpath, "newfile.txt"), "contents")
        assert_paths_in_sync(self.cpath, self.spath)
        move(join(self.cpath, "newfile.txt"), "/home/markb/Documents/Program_repos/Fileserver/test.txt")
        assert_paths_in_sync(self.cpath, self.spath)
        remove("/home/markb/Documents/Program_repos/Fileserver/test.txt")

    def test_move_folder_outside_inside_with_tree(self):
        path = "/home/markb/Documents/Program_repos/Fileserver/test"
        mkdir(path)
        create(join(path, "newfile.txt"), "content")
        assert_paths_in_sync(self.cpath, self.spath)
        move(path, join(self.cpath, "newemptydir"))
        assert_paths_in_sync(self.cpath, self.spath)

    def test_change_file_subdirectory(self):
        mkdir(join(self.cpath, "subdirectory1"))
        mkdir(join(self.cpath, "subdirectory1/subdirectory2"))
        assert_paths_in_sync(self.cpath, self.spath)
        create(join(self.cpath, "subdirectory1/subdirectory2/newfile.txt"), "content")
        assert_paths_in_sync(self.cpath, self.spath)
        create(join(self.cpath, "subdirectory1/newfile.txt"), "content")
        assert_paths_in_sync(self.cpath, self.spath)
        move(join(self.cpath, "subdirectory1/subdirectory2"), join(self.cpath, "subdirectory2"))
        assert_paths_in_sync(self.cpath, self.spath)

    def test_add_single_file(self):
        create(join(self.cpath, "newfile.txt"), "contents")
        assert_paths_in_sync(self.cpath, self.spath)

    def test_single_file_completely_changes_3_times(self):
        create(join(self.cpath, "newfile.txt"), "contents")
        assert_paths_in_sync(self.cpath, self.spath)

        create(join(self.cpath, "newfile.txt"), "contents more")
        assert_paths_in_sync(self.cpath, self.spath)

        create(join(self.cpath, "newfile.txt"), "beginning contents more")
        assert_paths_in_sync(self.cpath, self.spath)

        create(join(self.cpath, "newfile.txt"), "new content")
        assert_paths_in_sync(self.cpath, self.spath)

    def test_single_file_change_and_remove(self):
        create(join(self.cpath, "newfile.txt"), "contents")
        assert_paths_in_sync(self.cpath, self.spath)

        remove(join(self.cpath, "newfile.txt"))
        assert_paths_in_sync(self.cpath, self.spath)

    def test_add_empty_dir(self):
        mkdir(join(self.cpath, "newemptydir"))
        assert_paths_in_sync(self.cpath, self.spath)

    def test_add_and_change_dir_name(self):
        mkdir(join(self.cpath, "newemptydir"))
        rename(join(self.cpath, "newemptydir"), join(self.cpath, "new_empty_dir"))
        assert_paths_in_sync(self.cpath, self.spath)

    def test_add_and_remove_empty_dir(self):
        mkdir(join(self.cpath, "newemptydir"))
        assert_paths_in_sync(self.cpath, self.spath)

        rmtree(join(self.cpath, "newemptydir"))
        assert_paths_in_sync(self.cpath, self.spath)

    def test_3_new_files_1mb_each_add_instantly(self):
        create(join(self.cpath, "file1.txt"), "*" * 10 ** 6)
        create(join(self.cpath, "file2.txt"), "*" * 10 ** 6)
        create(join(self.cpath, "file3.txt"), "*" * 10 ** 6)
        assert_paths_in_sync(self.cpath, self.spath)

    def test_3_new_files_1mb_each_add_with_delay(self):
        create(join(self.cpath, "file1.txt"), "*" * 10 ** 6)
        create(join(self.cpath, "file2.txt"), "*" * 10 ** 6)
        create(join(self.cpath, "file3.txt"), "*" * 10 ** 6)
        assert_paths_in_sync(self.cpath, self.spath)

    def test_single_file_change_1_byte_beginning(self):
        create(join(self.cpath, "file1.txt"), "0" + "*" * 10 ** 6)
        assert_paths_in_sync(self.cpath, self.spath)

        create(join(self.cpath, "file1.txt"), "1" + "*" * 10 ** 6)
        assert_paths_in_sync(self.cpath, self.spath)

    def test_1_empty_file(self):
        create(join(self.cpath, "file1.txt"), "")
        assert_paths_in_sync(self.cpath, self.spath)

    def test_3_empty_files_add_instantly(self):
        create(join(self.cpath, "file1.txt"), "")
        create(join(self.cpath, "file2.txt"), "")
        create(join(self.cpath, "file3.txt"), "")
        assert_paths_in_sync(self.cpath, self.spath)

    def test_3_empty_files_add_with_delay(self):
        create(join(self.cpath, "file1.txt"), "")
        create(join(self.cpath, "file2.txt"), "")
        create(join(self.cpath, "file3.txt"), "")
        assert_paths_in_sync(self.cpath, self.spath)

    def test_1_file_grows_twice_with_delay(self):
        create(join(self.cpath, "file1.txt"), "*" * 10 ** 6)
        assert_paths_in_sync(self.cpath, self.spath)
        create(join(self.cpath, "file1.txt"), "*" * 20 ** 6)
        assert_paths_in_sync(self.cpath, self.spath)

    def test_1_file_shrinks_twice_with_delay(self):
        create(join(self.cpath, "file1.txt"), "*" * 20 ** 6)
        assert_paths_in_sync(self.cpath, self.spath)
        create(join(self.cpath, "file1.txt"), "*" * 10 ** 6)
        assert_paths_in_sync(self.cpath, self.spath)

    def test_many_small_files(self):
        for i in range(0, 5000):
            create(join(self.cpath, "file_%i.txt" % (i,)), "contents_%i" % (i,))

        assert_paths_in_sync(self.cpath, self.spath)

    def test_many_large_files(self):
        for i in range(0, 5000):
            create(join(self.cpath, "file_%i.txt" % (i,)), "*" * 10 ** 6)

        assert_paths_in_sync(self.cpath, self.spath)

    def test_very_big_file(self):
        create(join(self.cpath, "file1.txt"), "*" * 4 * 10 ** 9)
        assert_paths_in_sync(self.cpath, self.spath)


    def test_file_to_empty_dirs_and_back(self):
        for i in range(0, 10):
            create(join(self.cpath, "file_%i" % (i,)), "contents_%i" % (i,))
        assert_paths_in_sync(self.cpath, self.spath)
       
        wipe_path(self.cpath)
        for i in range(0, 10):
            mkdir(join(self.cpath, "file_%i" % (i,)))
        assert_paths_in_sync(self.cpath, self.spath)
    
        wipe_path(self.cpath)
        for i in range(0, 10):
            create(join(self.cpath, "file_%i" % (i,)), "contents_%i" % (i,))
        assert_paths_in_sync(self.cpath, self.spath)

# Ensures that folders and synced even if the folders contain different stuff before they get started!
class TestInitialSync(TestCase):
    pass
    def setUp(self):
        self.spath = SERVER_PATH
        self.cpath = CLIENT_PATH
        reset_path(self.spath)
        reset_path(self.cpath)
        port = find_free_port()
        self.server_cmd = environ["SERVER_CMD"].format(port=port, path=self.spath)
        self.client_cmd = environ["CLIENT_CMD"].format(port=port, path=self.cpath)
        print(self.server_cmd)
        print(self.client_cmd)

    def tearDown(self):
        self.server_process.shutdown()
        self.client_process.shutdown()

    def test_one_file(self):
        create(join(self.cpath, "newfile.txt"), "contents")

        self.server_process = Process(self.server_cmd)
        sleep(1.0)
        self.client_process = Process(self.client_cmd)
        sleep(1.0)
        assert_paths_in_sync(self.cpath, self.spath)

    def test_file_and_empty_dir(self):
        create(join(self.cpath, "newfile.txt"), "contents")
        mkdir(join(self.cpath, "newemptydir"))

        self.server_process = Process(self.server_cmd)
        sleep(1.0)
        self.client_process = Process(self.client_cmd)
        sleep(1.0)
        assert_paths_in_sync(self.cpath, self.spath)
