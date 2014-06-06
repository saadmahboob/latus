
import os
import core.db
import core.metadatapath
import test.util
import test.results
import test.create_files
from test.conftest import setup

def test_scan_simple(setup):
    db = core.db.DB(test.create_files.get_simple_root(), core.metadatapath.MetadataPath(test.create_files.get_metadata_root()), force_drop=True)
    db.scan()
    a_path = os.path.join(test.create_files.SRC, test.create_files.A_FILE_NAME)
    assert(a_path != None)
    if a_path is not None:
        sha512_val = db.get_file_info(a_path).sha512
        assert(sha512_val == test.results.sha512[test.create_files.A_STRING])
    assert(db.get_root() == os.path.abspath(test.create_files.get_simple_root()))

def test_scan_unicode(setup):
    db = core.db.DB(test.create_files.get_unicode_root(), core.metadatapath.MetadataPath(test.create_files.get_metadata_root()), force_drop=True)
    db.scan()

def test_new_root(setup):
    db = core.db.DB(test.create_files.get_simple_root(), core.metadatapath.MetadataPath(test.create_files.get_metadata_root()), force_drop=True)
    db.scan()
    db = core.db.DB(test.create_files.get_unicode_root(), core.metadatapath.MetadataPath(test.create_files.get_metadata_root()))
    db.scan()

def test_hash_time(setup):
    db = core.db.DB(test.create_files.get_hash_root(), core.metadatapath.MetadataPath(os.path.join(test.create_files.get_metadata_root(), 'hashtime')))
    db.scan()