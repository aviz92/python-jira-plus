class ProjectNotAllowedError(PermissionError):
    """Raised when an operation targets a project outside the client's `allowed_projects`."""
