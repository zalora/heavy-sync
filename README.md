# heavy-sync

`heavy-sync` is created to address the pain with current tools (`s3cmd sync`,
`gsutil rsync`, `aws s3 sync`) when dealing with large buckets (containing
millions of objects). Goals:

  - Everything that can be retried, should be retried
  - Everything that can be resumed, should be resumed
  - Ultimately, every bucket synchronization that can be finished, should be
    finished

Supported service providers: Amazon Simple Storage Service (AWS S3), Google
Cloud Storage (GCS).

## How it works

 1. Generate a list of objects (files) at the source and the destination. Both
    lists are stored in a SQLite database.
 2. Copy objects that are new or have changed (based on the md5 checksum) over.
    Each sucessfull transfer is recorded in the SQLite database.
 3. Delete, from the destination bucket, objects that have disappeared from the
    source bucket.
 4. If a non-zero threshold is provided, delete old object versions that are
    older than the threshold.

Usually, step 2 takes the bulk of the time and is where other tools will fail
(timeout, broken pipe or just hang). When they fail, the whole operation needs
to be started from scratch. For big buckets this can be a show stopper, as the
synchronization is unlikely to finish without any interruption.

`heavy-sync` can resume a previously interrupted sync. As long as step 1
finishes sucessfully, progress is never lost. Transient errors are retried
forever. 404 errors are ignored. Other errors should cause the program to exit
with an non-zero code. Of course, the object listings may get out of date
during the sync (it can take hours for the listing and days for the rest), but
that's generally not a problem.

# heavy-check

`heavy-check` chooses a random file in the source bucket, then tries
downloading that file from the destination bucket, and verifies the checksum.
Attention is paid so that randomness is preserved without first loading the
whole object list into memory.

If `heavy-sync` is used to backup a bucket from one service to another,
`heavy-check` can be used to check the backup. Normally, your certainty about
your backups reduces over time. With a daily `heavy-check`, however, it will be
increasing instead. TODO: boost this certainty by checking more than one file
at a time.
