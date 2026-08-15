"""Background job definitions.

Jobs are idempotent, take identifiers rather than objects, and report progress through
the database so a process restart never orphans work invisibly.
"""
