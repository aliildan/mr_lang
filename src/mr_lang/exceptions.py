"""Structured exception hierarchy for mr_lang."""


class MrLangError(Exception):
    """Base exception for all mr_lang errors."""


class ConfigError(MrLangError):
    """Configuration loading or validation error."""


class ProviderError(MrLangError):
    """Model provider initialization or invocation error."""


class ToolError(MrLangError):
    """Tool registration, discovery, or execution error."""


class SkillError(MrLangError):
    """Skill loading, validation, or activation error."""


class WorkspaceError(MrLangError):
    """Workspace loading or validation error."""


class AdapterError(MrLangError):
    """Adapter lifecycle or message handling error."""
