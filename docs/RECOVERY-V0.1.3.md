# v0.1.3 verification-dispatch recovery

ProdKit Workflows v0.1.3 published successfully at exact source `89eec1f6bcd4e45fb67c9fa99122ea6feba9d4bc`, but the parent `Release` run failed in its post-publication verification-dispatch job.

The dispatcher embedded `source_sha: ${{ github.sha }}` literally inside a `run:` script while validating the immutable verification caller. GitHub Actions interpolated that expression before Python executed, so the runtime validator searched the caller source for the concrete SHA instead of the required expression and failed closed.

The permanent correction constructs the expected expression at runtime so Actions cannot pre-expand it. A dedicated regression guard rejects reintroduction of the interpolated form.

The v0.1.3 tag and published assets remain immutable. Final cleanup must independently verify the exact publication and the known failed tail before deleting the release/recovery branches.
