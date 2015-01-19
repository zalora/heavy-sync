`heavy-sync` is created to address the pain points with current tools (`s3cmd sync`, `gsutil rsync`, `aws s3 sync`) when dealing with large buckets (containing millions of objects). Goals:

  - Everything that can be retried, should be retried
  - Everything that can be resumed, should be resumed
  - Ultimately, every bucket synchronization that can be finished, should be finished

## How it works

 1. Generate a list of objects (files) at the source and the destination. Both lists are stored in a SQLite database.
 2. Copy objects that are new or have changed (based on the md5 checksum) over. Each sucessfull transfer is recorded in the SQLite database.
 3. Delete, from the destination bucket, objects that have disappeared from the source bucket.
 4. TODO: delete old object versions that are older than a certain threshold.

Usually, step 2 takes the bulk of the time and is where other tools will fail (timeout, broken pipe or just hang). When they fail, the whole operation needs to be started from scratch. For big buckets this can be a show stopper, as the synchronization is unlikely to finish without any interruption.

`heavy-sync` can resume a previously interrupted sync. As long as step 1 finishes sucessfully, progress is never lost. Transient errors are retried forever. 404 errors are ignored. Other errors should cause the program to exit with an non-zero code. Of course, the object listings may get out of date during the sync (it can take hours for the listing and days for the rest), but that's generally not a problem.
