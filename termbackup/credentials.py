"""Secure credential storage using OS keyring."""

SERVICE_NAME = "termbackup"
TOKEN_KEY = "github_token"
PASSWORD_PREFIX = "profile_password_"


def save_token(token: str):
    """Saves the GitHub token to the OS keyring."""
    import keyring

    keyring.set_password(SERVICE_NAME, TOKEN_KEY, token)


def get_token() -> str | None:
    """Retrieves the GitHub token from the OS keyring."""
    import keyring

    return keyring.get_password(SERVICE_NAME, TOKEN_KEY)


def delete_token():
    """Removes the GitHub token from the OS keyring."""
    import keyring

    try:
        keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass


def save_profile_password(profile_name: str, password: str):
    """Saves a profile's backup password to the keyring (for scheduled runs)."""
    import keyring

    keyring.set_password(SERVICE_NAME, f"{PASSWORD_PREFIX}{profile_name}", password)


def get_profile_password(profile_name: str) -> str | None:
    """Retrieves a profile's backup password from the keyring."""
    import keyring

    return keyring.get_password(SERVICE_NAME, f"{PASSWORD_PREFIX}{profile_name}")
