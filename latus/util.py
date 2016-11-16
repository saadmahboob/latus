import os
import platform
import uuid
import datetime
import appdirs
import random
import time

import latus.logger
import latus.const


def is_windows():
    return platform.system().lower()[0] == 'w'


def is_linux():
    return platform.system().lower()[0] == 'l'


def is_mac():
    # darwin
    return platform.system().lower()[0] == 'd'

if is_windows():
    import win32api
    import win32con


def get_long_abs_path(in_path):
    # Trick to get around 260 char limit
    # http://msdn.microsoft.com/en-us/library/aa365247.aspx#maxpath
    long_prefix = "\\\\?\\"
    prefix_len = len(long_prefix)
    starts_with = in_path[:4].startswith(long_prefix)
    if is_windows() and ((len(in_path) < prefix_len) or not starts_with):
        abs_path = long_prefix + os.path.abspath(in_path)
    else:
        abs_path = os.path.abspath(in_path)
    if os.path.isdir(abs_path):
        abs_path += os.sep
    return abs_path


# if this path has a drive specifier (as found in Windows), remove it
def remove_drive_spec(p):
    if p[0].isalpha() and p[1] == ":":
        p = os.path.splitdrive(p)[1]
    return p


def get_abs_path_wo_drive(p):
    p = os.path.abspath(p)
    is_dir = os.path.isdir(p)
    p = remove_drive_spec(p)
    if is_dir:
        p += os.sep
    return p


def del_files(file_list):
    for f in file_list:
        if os.path.exists(f):
            os.remove(f)


def is_hidden(in_path):
    is_hidden_flag = False
    attrib = 0
    if is_windows():
        long_abs_path = get_long_abs_path(in_path)
        try:
            attrib = win32api.GetFileAttributes(long_abs_path)
        except: ## pywintypes.error:  todo: pywintypes.error seems to be wrong ... find the correct way to do this
            latus.logger.log.error(long_abs_path)
        is_hidden_flag = (attrib & win32con.FILE_ATTRIBUTE_HIDDEN > 0)
    return is_hidden_flag


def is_system(in_path):
    is_system_flag = False
    attrib = 0
    if is_windows():
        long_abs_path = get_long_abs_path(in_path)
        try:
            attrib = win32api.GetFileAttributes(long_abs_path)
        except:  ## pywintypes.error:  todo: pywintypes.error seems to be wrong ... find the correct way to do this
            latus.logger.log.error(long_abs_path)
        is_system_flag = (attrib & win32con.FILE_ATTRIBUTE_SYSTEM > 0)
    return is_system_flag


def make_hidden(in_path):
    # for Linux/Mac the file needs to begin with a dot, therefore there's not really anything to do for these platforms
    if is_windows():
        attribute = win32api.GetFileAttributes(in_path)
        if not (attribute & win32con.FILE_ATTRIBUTE_HIDDEN):
            win32api.SetFileAttributes(in_path, win32con.FILE_ATTRIBUTE_HIDDEN)
    # todo: check that the file name does indeed start with a dot


def make_dirs(path):
    """
    Make a directory as specified by path.  If it already exists, simply return (don't raise an error).

    :param path: path of directories/folders to create
    """
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


def make_dir(path, hidden=False):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass
    if hidden:
        make_hidden(path)


def get_latus_guid():
    """
    This is a GUID we can include in files to ensure it comes from this program.  For example, when we generate
    a key or a database we can put this GUID in there to prevent aliasing and collisions.  Note that this doesn't
    prohibit maliciousness - it only prevents accidental 'good faith' collisions.
    :return: the latus GUID as a string
    """
    guid = '3E7A7DB0-3B15-416E-93D6-0FCF52BAEA38'
    return guid


def new_node_id():
    return str(uuid.uuid4())


def wait_random(sec):
    """
    wait between 1 and sec seconds
    :param sec: maximum time to wait (in seconds)
    :return: time waited (in seconds)
    """
    t = (sec - 1.0) * random.random() + 1.0
    time.sleep(t)
    return t


def version_to_tuple(version_string):
    """
    convert a version string to a version tuple
    :param version_string: e.g. '2.5.1'
    :return: version tuple, e.g. (2,5,1)
    """
    return tuple([int(s) for s in version_string.split('.')])