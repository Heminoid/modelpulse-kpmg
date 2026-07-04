"""DataFrame and column-name utility functions."""


def normalize_col_name(name: str) -> str:
    """Normalize a column name for heuristic matching.

    Strips whitespace, lowercases, and removes underscores, hyphens,
    spaces, and dots so that 'Application ID', 'application_id',
    'ApplicationID', and 'application-id' all normalize to 'applicationid'.
    """
    return (
        name.strip()
        .lower()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .replace(".", "")
    )
