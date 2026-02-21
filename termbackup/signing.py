"""Ed25519 backup signing (optional feature)."""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from termbackup.config import CONFIG_DIR

SIGNING_KEY_PATH = CONFIG_DIR / "signing_key.pem"
SIGNING_PUB_PATH = CONFIG_DIR / "signing_key.pub"


def has_signing_key() -> bool:
    """Checks if an Ed25519 signing keypair exists."""
    return SIGNING_KEY_PATH.exists() and SIGNING_PUB_PATH.exists()


def generate_signing_key(password: str) -> None:
    """Generates an Ed25519 keypair, encrypted with the given password."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()

    # Write encrypted private key
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
    )
    SIGNING_KEY_PATH.write_bytes(pem_private)

    # Write public key
    pem_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    SIGNING_PUB_PATH.write_bytes(pem_public)

    # Set permissions on Unix
    _set_file_permissions(SIGNING_KEY_PATH)
    _set_file_permissions(SIGNING_PUB_PATH)


def sign_archive(archive_path: Path, password: str) -> bytes:
    """Signs an archive file with the Ed25519 private key.

    Returns:
        64-byte Ed25519 signature.
    """
    pem_data = SIGNING_KEY_PATH.read_bytes()
    private_key = serialization.load_pem_private_key(pem_data, password=password.encode())

    file_data = Path(archive_path).read_bytes()
    return private_key.sign(file_data)


def verify_signature(archive_path: Path, signature: bytes) -> bool:
    """Verifies an archive's Ed25519 signature against the public key."""
    pem_data = SIGNING_PUB_PATH.read_bytes()
    public_key = serialization.load_pem_public_key(pem_data)

    file_data = Path(archive_path).read_bytes()
    try:
        public_key.verify(signature, file_data)
        return True
    except Exception:
        return False


def _set_file_permissions(file_path: Path) -> None:
    """Sets restrictive file permissions on Unix systems."""
    import os
    import platform
    import stat

    if platform.system() != "Windows":
        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
