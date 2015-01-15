#!/usr/bin/env python

from multiprocessing.pool import ThreadPool
from os import path, rename
from time import time
from boto.exception import GSResponseError
from boto.gs.key import Key as GSKey
from boto.s3.key import Key as S3Key

import boto
import sqlite3
import sys
import tempfile

# Seemingly unused but needed for GCS authentication
import gcs_oauth2_boto_plugin


s_bucket_uri = sys.argv[1]
d_bucket_uri = sys.argv[2]


def get_bucket(bucket_uri, validate=False):
    scheme = bucket_uri[:2]
    bucket_name = bucket_uri[5:]
    boto_connection = {
        'gs': boto.connect_gs,
        's3': boto.connect_s3,
    }[scheme]()
    return boto_connection.get_bucket(bucket_name, validate=validate)


def get_key(bucket_uri, path):
    scheme = bucket_uri[:2]
    constructor = {
        'gs': GSKey,
        's3': S3Key,
    }[scheme]
    return constructor(get_bucket(bucket_uri), path)


# Populate the table with the contents of the bucket
def fetch(bucket_uri, sqlite_connection, table):
    bucket = get_bucket(bucket_uri, validate=True)
    for key in bucket.list():
        sqlite_connection.execute('INSERT INTO %s (bucket, path, hash) VALUES (?, ?, ?)' % table,
                           (bucket_uri, key.name, key.etag))


# Upload a path
# Return True if the underlying command exits with code 0, False otherwise
# TODO: Handle errors
def upload(path):
    # Roll over when hitting 10 MB
    f = tempfile.SpooledTemporaryFile(max_size=10*2**20)
    get_key(s_bucket_uri, path).get_contents_to_file(f)
    get_key(d_bucket_uri, path).set_contents_from_file(f, rewind=True)
    return path


def upload_row(row):
    return upload(row[0])


def remove(path):
    bucket = get_bucket(d_bucket_uri)
    try:
        bucket.delete_key(path)
    except GSResponseError as e:
        if e.status != 404:
            raise


# Continue a previous run
def resume(connection):

    print 'Skipping over up-to-date objects...'
    connection.execute('''
        UPDATE source SET processed = 1
        WHERE rowid IN (
            SELECT s.rowid FROM source s JOIN destination d
            ON s.path = d.path AND s.hash = d.hash
        )
    ''')

    print 'Uploading new/updated objects from source to destination...'
    sql_it = connection.execute('''SELECT path FROM source WHERE NOT processed''')
    pool = ThreadPool()
    pool_it = pool.imap_unordered(upload_row, list(sql_it))
    for path in pool_it:
        connection.execute('''UPDATE source SET processed = 1 WHERE path = ?''', (path,))
        print 'Finished: %s' % path

    print 'Deleting objects in destination that have been deleted in source...'
    for row in connection.execute('''
        SELECT d.rowid, d.path
        FROM destination d LEFT JOIN source s
        ON d.path = s.path WHERE s.path IS NULL
    '''):
        remove(row[1])
        connection.execute('''DELETE FROM destination WHERE rowid = ?''', (row[0],))


def new_run(connection):

    connection.executescript('''
        CREATE TABLE source (bucket VARCHAR,
                             path VARCHAR,
                             hash VARCHAR,
                             processed BOOLEAN DEFAULT 0);
        CREATE TABLE destination (bucket VARCHAR, path VARCHAR, hash VARCHAR);
        CREATE INDEX IF NOT EXISTS source_path_index ON source (path);
        CREATE INDEX IF NOT EXISTS source_hash_index ON source (hash);
        CREATE INDEX IF NOT EXISTS destination_path_index ON destination (path);
        CREATE INDEX IF NOT EXISTS destination_hash_index ON destination (hash);
    ''')

    fetch(s_bucket_uri, connection, 'source')
    fetch(d_bucket_uri, connection, 'destination')

    resume(connection)


def main():

    if path.exists('sync.sqlite'):
        connection = sqlite3.connect('sync.sqlite', isolation_level=None)
        cursor = connection.cursor()
        cursor.execute('''SELECT 1 FROM source WHERE NOT processed LIMIT 1''')

        if cursor.fetchone() is not None:
            print 'Unfinished state data found. Resuming...'
            resume(connection)
            return
        else:
            connection.close()
            rename('sync.sqlite', 'sync.sqlite-%s' % int(time()))

    connection = sqlite3.connect('sync.sqlite', isolation_level=None)
    new_run(connection)


main()
