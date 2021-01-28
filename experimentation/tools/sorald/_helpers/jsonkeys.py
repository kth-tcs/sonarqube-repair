"""Constants for JSON keys used primarily in the PR recorder."""

class TOP_LEVEL:
    """The top-level keys."""
    REPO_SLUG = "repoSlug"

class PR:
    """Keys for PR metadata."""

    SECTION_KEY = "prMetadata"
    URL = "url"
    CREATED_AT = "createdAt"
    CLOSED_AT = "closedAt"
    MERGED_AT = "mergedAt"
    REPO_SLUG = "repoSlug"
    NUMBER = "number"
    STATE = "state"
    IS_MERGED = "isMerged"


class DIFF:
    """Keys for diff data."""

    SECTION_KEY = "diffs"
    INITIAL = "initial"
    FINAL = "final"


class RECORD:
    """Keys for record metadata."""

    SECTION_KEY = "recordMetadata"
    CREATED_AT = "createdAt"
    LAST_MODIFIED = "lastModified"


class MANUAL_EDITS:
    """Keys for the manual edits data."""

    SECTION_KEY = "manualEdits"
    BEFORE_OPEN_PR = "beforeOpenPr"
    AFTER_OPEN_PR = "afterOpenPr"


class SORALD_STATS:
    """Keys for the Sorald statistics."""

    SECTION_KEY = "soraldStatistics"
    REPAIRS = "repairs"
