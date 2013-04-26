
# latus-wide testing routines

import os
import shutil
import time
from .. import util, const

SRC = "src"
DEST_EMPTY = "dest_empty"
DEST_EXISTS_EXACT = "dest_exists_exact"
DEST_EXISTS_DIFFERENT = "dest_exists_different"
DEST_EXISTS_UNDER_DIFFERENT_NAME = "dest_exists_under_different_name"

# something to give good unicode coverage ...
N_UNICODE = 63
TEST_MAX_CODE = 8192

class test_latus():

    # This writes various input files.  The goal is to not have to package up test files in the repo, if we
    # can avoid it.  Also, this way we can readily re-initialize and fully clean up test files.
    def write_files(self, force = False, write_flag = True):
        test_string = "a"
        different_test_string = "b"
        a_file_name = "a.txt"

        self.files_written = 0
        util.del_files((os.path.join(get_root(), const.METADATA_DIR_NAME, const.LFS_DB_NAME + const.DB_EXT),
                       os.path.join(get_simple_root(), const.METADATA_DIR_NAME, const.LFS_DB_NAME + const.DB_EXT),
                       os.path.join(get_simple_root(), const.OUTPUT_FILE)))

        if force or not os.path.exists(get_simple_root()):
            self.write_to_file(os.path.join(get_simple_root(), SRC, a_file_name), test_string, write_flag)
            make_dirs(os.path.join(get_simple_root(), DEST_EMPTY))
            self.write_to_file(os.path.join(get_simple_root(), DEST_EXISTS_EXACT, a_file_name), test_string, write_flag)
            self.write_to_file(os.path.join(get_simple_root(), DEST_EXISTS_DIFFERENT, a_file_name), different_test_string, write_flag)
            self.write_to_file(os.path.join(get_simple_root(), DEST_EXISTS_UNDER_DIFFERENT_NAME, "a_but_different_name.txt"), test_string, write_flag)
        if force or not os.path.exists(get_unicode_root()):
            self.write_unicode_files(get_unicode_root(), test_string, write_flag)
        if force or not os.path.exists(get_mtime_root()):
            f = os.path.join(get_mtime_root(), a_file_name)
            t = get_mtime_time()
            self.write_to_file(f, test_string, write_flag)
            os.utime(f, (t, t))

        return self.files_written

    # note that this makes the required dirs if necessary
    def write_to_file(self, p, contents, write_flag):
        # turn off writing to enable us to merely count the files we would have written
        # (we need to know how many files written for testing purposes)
        if write_flag:
            d = os.path.dirname(p)
            make_dirs(d)
            f = open(p, "w")
            f.write(contents)
            f.close()
        self.files_written += 1

    def write_unicode_files(self, root_dir, test_string, write_flag):
        paths = get_unicode_file_paths(root_dir)
        for file_path in paths:
            self.write_to_file(file_path, test_string, write_flag)

    def clean(self):
        shutil.rmtree(get_root())

def get_root():
    # must not match nose's regex for test files/directories below the main directory "test",
    # since nose errors out on the unicode files
    return os.path.join("test", "data")

def get_unicode_root():
    return os.path.join(get_root(), "unicode")

def get_simple_root():
    return os.path.join(get_root(), "simple")

def get_mtime_root():
    return os.path.join(get_root(), "mtime")

def get_mtime_time():
    return time.mktime(time.strptime("12", "%y"))

def make_dirs(p):
    if not os.path.exists(p):
        os.makedirs(p)

def make_unicode_string(start, length, inc = 1):
    out_string = ''
    char_codepoint = start
    # Avoid / and \ so we don't mistakenly create a folder, as well as other illegal filename chars
    illegal_chars = [ '/', "\\", ";", "*", "?", '"', "<", ">", "|", ":"]
    while len(out_string) < length:
        unicode_char = chr(char_codepoint)
        if (char_codepoint >= ord(' ')) and not (unicode_char in illegal_chars):
            out_string = out_string + unicode_char
        char_codepoint = char_codepoint + inc
    return out_string

def get_unicode_file_paths(root_dir):
    paths = []
    space = 32 # ' '
    length = N_UNICODE
    max_code =  TEST_MAX_CODE - space # fairly arbitrary max - perhaps this should be a different value?
    for start in range(space, max_code, length):
        # start and end with something always valid
        file_name = 'A' + make_unicode_string(start, length) + '.txt'
        paths.append(os.path.join(root_dir, file_name))
    return paths

