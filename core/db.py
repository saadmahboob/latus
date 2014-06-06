
import os
import platform
import hashlib
import core.logger
import core.util
import core.walker
import core.hash
import core.const
import datetime
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative

Base = sqlalchemy.ext.declarative.declarative_base()

class Roots(Base):
    """
    Allows the 'files' table to have entries that are from multiple roots
    """
    __tablename__ = 'roots'
    absroot = sqlalchemy.Column(sqlalchemy.String, primary_key=True)

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
    absroot = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey("roots.absroot"))
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
    absroot = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey("roots.absroot"))
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
        digest = hashlib.sha512()
        digest.update(self.absroot.encode())
        absroot_sha512 = digest.hexdigest()


        self.sqlite_db_path = 'sqlite:///' + "/".join(metadata_path.db_folder_as_list) + "/" + id + self.DB_EXT
        self.engine = sqlalchemy.create_engine(self.sqlite_db_path)
        Session = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = Session()

        if force_drop:
            Base.metadata.drop_all(self.engine)

        # if no common table then we have nothing, so create everything
        if not self.engine.has_table(Common.__tablename__):
            Base.metadata.create_all(self.engine)

            self.session.add(Common(key='updatetime', val=str(datetime.datetime.utcnow())))

            # meed to know roughly the kind of machine to make use of the HashPerf values
            self.session.add(Common(key='processor', val=platform.processor()))
            self.session.add(Common(key='machine', val=platform.machine()))

            self.session.commit()

        if self.session.query(Roots).filter(Roots.absroot == self.absroot).count() == 0:
            self.session.add(Roots(absroot=self.absroot))

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
                    self.set_hash_perf(self.absroot, rel_path, sha512_time)
                file_info = Files(absroot=self.absroot, path=rel_path, sha512=sha512, size=size, mtime=mtime, hidden=hidden, system=system)
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
        return self.session.query(Roots).one().absroot

    def set_hash_perf(self, absroot, path, time):
        """
        Potentially update the hash performance with this hash value.  We only keep around the longest values,
         so if this isn't one of those it may not be put into the table.
        :param path:  relative file path
        :param time: time it took to do the hash (in seconds)
        :return: True if it was used, False otherwise
        """
        used = False
        # The table holds only the largest values we've seen.  So if this time is shorter than the shortest time in
        # the table, ignore it.
        full = self.session.query(HashPerf).count() >= core.const.MAX_HASH_PERF_VALUES
        shortest_time_row = self.session.query(HashPerf).order_by(HashPerf.time).first()
        if not full or shortest_time_row is None or time > shortest_time_row.time:
            # update for this path
            row_for_this_path = self.session.query(HashPerf).filter(HashPerf.absroot == absroot, HashPerf.path == path)
            if row_for_this_path.count() > 0:
                row_for_this_path.delete()
            elif full:
                # if we're full, first delete the entry with the shortest time
                self.session.delete(self.session.query(HashPerf).order_by(HashPerf.time).first())
            hash_perf = HashPerf(absroot=absroot, path=path, time=time)
            self.session.add(hash_perf)
            used = True
        return used
