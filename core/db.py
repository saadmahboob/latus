
import os
import core.logger
import core.util
import core.walker
import core.hash
import datetime
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative

Base = sqlalchemy.ext.declarative.declarative_base()

class Common(Base):
    """
    Values that are common across other tables (e.g. root path)
    """
    __tablename__ = 'common'
    key = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    val = sqlalchemy.Column(sqlalchemy.String)

class Files(Base):
    """
    File info.  This is a list of file changes (AKA 'events').
    """
    __tablename__ = 'files'
    path = sqlalchemy.Column(sqlalchemy.String) # path (off of root) for this file
    sha512 = sqlalchemy.Column(sqlalchemy.String) # sha512 for this file
    size = sqlalchemy.Column(sqlalchemy.BigInteger) # size of this file
    mtime = sqlalchemy.Column(sqlalchemy.DateTime) # most recent modification time of this file (UTC)
    hidden = sqlalchemy.Column(sqlalchemy.Boolean) # does this file have the hidden attribute set?
    system = sqlalchemy.Column(sqlalchemy.Boolean) # does this file have the system attribute set?
    count = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True) # todo: be careful with this if we do a trim on this table

class HashPerf(Base):
    """
    Hash calculation performance.  This is a separate table since we only keep the longest N times.
    """
    __tablename__ = 'hashperf'
    path = sqlalchemy.Column(sqlalchemy.String, primary_key=True) # path to the file (from this we can get its size)
    time = sqlalchemy.Column(sqlalchemy.Float) # time in seconds to took to calculate the hash

class DB:
    DB_EXT = '.db'
    def __init__(self, root, metadata_path, id = 'fs', force_drop = False):
        """
        root is the root folder of the filesystem
        metadata_path is an instance of the MetadataPath class that has the metadata folder
        id is used to create the mysql database filename
        force_drop forces any existing tables to be dropped (good for testing, manual nuking of the db, etc.)
        """
        self.log = core.logger.log
        self.absroot = os.path.abspath(root) # for the metdata, we always need to use the abspath (the full path)
        del root # make sure we don't use this non-absolute ( non-abspath() ) version

        self.sqlite_db_path = 'sqlite:///' + "/".join(metadata_path.db_folder_as_list) + "/" + id + self.DB_EXT
        self.engine = sqlalchemy.create_engine(self.sqlite_db_path)
        Session = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = Session()

        if force_drop:
            Base.metadata.drop_all(self.engine)

        if self.engine.has_table(Common.__tablename__):
            if self.get_root() != self.absroot:
                self.log.warning("new root: " + self.absroot + " was:" + self.get_root() + " - dropping all existing tables")
                Base.metadata.drop_all(self.engine)

        if not self.engine.has_table(Common.__tablename__):
            Base.metadata.create_all(self.engine)
            self.session.add(Common(key = 'absroot', val = self.absroot))
            self.session.add(Common(key = 'updatetime', val = str(datetime.datetime.utcnow())))
            self.session.commit()

    def commit(self):
        self.session.query(Common).filter(Common.key == 'updatetime').update({"val" : str(datetime.datetime.utcnow())})
        self.session.commit()

    def is_time_different(self, time_a, time_b):
        return abs(time_a - time_b) > datetime.timedelta(seconds=1)

    def put_file_info(self, rel_path):
        full_path = os.path.join(self.absroot, rel_path)
        # todo: handle when file deleted
        if not core.util.is_locked(full_path):
            mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(full_path))
            size = os.path.getsize(full_path)
            # get the most recent row for this file
            db_entry = self.session.query(Files).filter(Files.path == rel_path).order_by(-Files.count).first()
            # Test to see if the file is new or has been updated.
            # On the same (i.e. local) file system, for a given file path, if the mtime is the same then the contents
            # are assumed to be the same.  Note that there is some debate if file size is necessary here, but I'll
            # use it just to be safe.
            if db_entry is None or db_entry.size != size or self.is_time_different(db_entry.mtime, mtime):
                hidden = core.util.is_hidden(full_path)
                system = core.util.is_system(full_path)
                is_big = size >= core.const.BIG_FILE_SIZE # only time big files
                sha512, sha512_time = core.hash.calc_sha512(full_path, is_big)
                if is_big:
                    self.set_hash_perf(rel_path, sha512_time)
                file_info = Files(path = rel_path, sha512 = sha512, size = size, mtime = mtime, hidden = hidden, system = system)
                self.session.add(file_info)
                self.commit()

    def get_file_info(self, rel_path):
        db_entry = None
        if rel_path is None:
            self.log.warning("rel_path is None")
        else:
            db_entry = self.session.query(Files).filter(Files.path == rel_path).order_by(-Files.count).first()
            if db_entry is None:
                self.log.warning('not found in db:' + rel_path)
        return db_entry

    def scan(self):
        source_walker = core.walker.Walker(self.absroot)
        for file_path in source_walker:
            self.put_file_info(file_path)

    def get_common(self, key):
        """
        Retrieve a value from the common table
        :param key: key
        :return: value from the common table
        """
        db_entry = self.session.query(Common).filter(Common.key == key).one().val
        return db_entry

    def get_root(self):
        return self.get_common('absroot')

    def set_hash_perf(self, path, time):
        print("path", path, "time", time)
        if self.session.query(HashPerf).filter(HashPerf.path == path and HashPerf.time == time).count() == 0:
            if self.session.query(HashPerf).count() >= core.const.MAX_HASH_PERF_VALUES:
                # if we're full, delete the entry with the shortest time
                self.session.delete(self.session.query(HashPerf).order_by(HashPerf.time).first())
            hash_perf = HashPerf(path = path, time = time)
            self.session.add(hash_perf)

