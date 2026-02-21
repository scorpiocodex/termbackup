"""Custom .tbk binary archive format.

Supports two versions:
  - TBK1 (v1): AES-256-CBC + PBKDF2 + HMAC-SHA256
  - TBK2 (v2): AES-256-GCM + Argon2id (new default)
"""

import gzip
import io
import struct
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from termbackup import crypto
from termbackup.errors import ArchiveError, CryptoError
from termbackup.models import ArchiveHeader, ManifestData
from termbackup.utils import canonicalize_dict

# Archive format constants
MAGIC_V1 = b"TBK1"
MAGIC_V2 = b"TBK2"
VERSION_V1 = 1
VERSION_V2 = 2

# v2 KDF algorithm identifiers
KDF_ARGON2ID = 0x02

# v2 cipher suite identifiers
CIPHER_AES_256_GCM = 0x02


def _create_tarball_to_file(
    source_dir: Path,
    manifest: ManifestData | dict[str, Any],
    compression_level: int = 6,
) -> Path:
    """Creates a gzipped tarball to a temp file (streaming, low memory)."""
    # Support both Pydantic models and raw dicts
    if isinstance(manifest, ManifestData):
        manifest_dict = manifest.model_dump(mode="json")
        files = manifest.files
    else:
        manifest_dict = manifest
        files = manifest.get("files", [])

    # Write uncompressed tar to temp file first
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz")
    tmp_path = Path(tmp.name)

    try:
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            # Add manifest
            manifest_bytes = canonicalize_dict(manifest_dict).encode()
            tarinfo = tarfile.TarInfo(name="manifest.json")
            tarinfo.size = len(manifest_bytes)
            tar.addfile(tarinfo, io.BytesIO(manifest_bytes))

            # Add files from manifest
            for file_meta in files:
                rel_path = file_meta["relative_path"] if isinstance(file_meta, dict) else file_meta.relative_path
                file_path = source_dir / rel_path
                if file_path.exists():
                    tar.add(str(file_path), arcname=rel_path)

        tar_stream.seek(0)

        # Gzip to temp file
        with open(tmp_path, "wb") as f:
            with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=compression_level) as gz:
                gz.write(tar_stream.read())

        return tmp_path
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def create_archive(
    archive_path: Path,
    source_dir: Path,
    manifest: ManifestData | dict[str, Any],
    password: str,
    compression_level: int = 6,
):
    """Creates a .tbk v2 archive (AES-256-GCM + Argon2id)."""
    # 1. Create tar.gz payload to temp file
    tarball_path = _create_tarball_to_file(source_dir, manifest, compression_level)

    try:
        with open(tarball_path, "rb") as f:
            payload = f.read()
    finally:
        tarball_path.unlink(missing_ok=True)

    # 2. Encrypt the payload with v2 (AES-256-GCM + Argon2id)
    salt, nonce, ciphertext_with_tag = crypto.encrypt_v2(payload, password)

    # 3. Assemble the TBK2 archive file
    with open(archive_path, "wb") as f:
        # Magic + version
        f.write(MAGIC_V2)
        f.write(struct.pack("!B", VERSION_V2))

        # KDF algorithm
        f.write(struct.pack("!B", KDF_ARGON2ID))

        # KDF params: memory_cost (4B), time_cost (2B), parallelism (1B)
        f.write(struct.pack("!I", crypto.ARGON2_MEMORY_COST))
        f.write(struct.pack("!H", crypto.ARGON2_TIME_COST))
        f.write(struct.pack("!B", crypto.ARGON2_PARALLELISM))

        # Salt
        f.write(struct.pack("!B", len(salt)))
        f.write(salt)

        # Nonce
        f.write(struct.pack("!B", len(nonce)))
        f.write(nonce)

        # Cipher suite
        f.write(struct.pack("!B", CIPHER_AES_256_GCM))

        # Payload length + ciphertext (includes GCM tag)
        f.write(struct.pack("!Q", len(ciphertext_with_tag)))
        f.write(ciphertext_with_tag)


def _read_v1_header(f) -> ArchiveHeader:
    """Reads a TBK1 (v1) archive header."""
    version = struct.unpack("!B", f.read(1))[0]
    if version != VERSION_V1:
        raise ValueError(f"Unsupported v1 archive version: {version}")

    iterations = struct.unpack("!I", f.read(4))[0]
    salt_len = struct.unpack("!B", f.read(1))[0]
    salt = f.read(salt_len)
    iv_len = struct.unpack("!B", f.read(1))[0]
    iv = f.read(iv_len)
    payload_len = struct.unpack("!Q", f.read(8))[0]

    header_size = 4 + 1 + 4 + 1 + salt_len + 1 + iv_len + 8

    return ArchiveHeader(
        version=1,
        kdf_algorithm="pbkdf2",
        kdf_params={"iterations": iterations},
        salt=salt,
        iv_or_nonce=iv,
        payload_len=payload_len,
        header_size=header_size,
    )


def _read_v2_header(f) -> ArchiveHeader:
    """Reads a TBK2 (v2) archive header."""
    version = struct.unpack("!B", f.read(1))[0]
    if version != VERSION_V2:
        raise ValueError(f"Unsupported v2 archive version: {version}")

    kdf_algo = struct.unpack("!B", f.read(1))[0]

    memory_cost = struct.unpack("!I", f.read(4))[0]
    time_cost = struct.unpack("!H", f.read(2))[0]
    parallelism = struct.unpack("!B", f.read(1))[0]

    salt_len = struct.unpack("!B", f.read(1))[0]
    salt = f.read(salt_len)

    nonce_len = struct.unpack("!B", f.read(1))[0]
    nonce = f.read(nonce_len)

    struct.unpack("!B", f.read(1))  # cipher_suite (reserved)

    payload_len = struct.unpack("!Q", f.read(8))[0]

    # Header size: magic(4) + version(1) + kdf_algo(1) + memory(4) + time(2) + par(1)
    #              + salt_len(1) + salt + nonce_len(1) + nonce + cipher(1) + payload_len(8)
    header_size = 4 + 1 + 1 + 4 + 2 + 1 + 1 + salt_len + 1 + nonce_len + 1 + 8

    return ArchiveHeader(
        version=2,
        kdf_algorithm="argon2id" if kdf_algo == KDF_ARGON2ID else f"unknown({kdf_algo})",
        kdf_params={
            "memory_cost": memory_cost,
            "time_cost": time_cost,
            "parallelism": parallelism,
        },
        salt=salt,
        iv_or_nonce=nonce,
        payload_len=payload_len,
        header_size=header_size,
    )


def read_archive_header(archive_path: Path) -> ArchiveHeader:
    """Reads the header of a .tbk archive (auto-detects v1 vs v2)."""
    with open(archive_path, "rb") as f:
        magic = f.read(4)
        if magic == MAGIC_V1:
            return _read_v1_header(f)
        elif magic == MAGIC_V2:
            return _read_v2_header(f)
        else:
            raise ArchiveError(
                f"Not a valid .tbk archive (magic bytes: {magic!r}).",
                hint="This file may be corrupted or not a TermBackup archive.",
            )


def read_archive_payload(
    archive_path: Path,
    password: str,
    header: ArchiveHeader | dict[str, Any],
) -> bytes:
    """Reads and decrypts the payload of a .tbk archive (v1 or v2)."""
    # Support both ArchiveHeader model and legacy dict
    if isinstance(header, dict):
        version = header.get("version", 1)
        header_size = header["header_size"]
        salt = header["salt"]
        payload_len = header["payload_len"]
        iv_or_nonce = header.get("iv", header.get("iv_or_nonce", b""))
    else:
        version = header.version
        header_size = header.header_size
        salt = header.salt
        payload_len = header.payload_len
        iv_or_nonce = header.iv_or_nonce

    with open(archive_path, "rb") as f:
        f.seek(header_size)
        ciphertext = f.read(payload_len)

        try:
            if version == 1:
                hmac_signature = f.read(32)
                decrypted_payload = crypto.decrypt(
                    password, salt, iv_or_nonce, ciphertext, hmac_signature
                )
            else:
                # v2: ciphertext already includes GCM tag
                decrypted_payload = crypto.decrypt_v2(
                    password, salt, iv_or_nonce, ciphertext
                )
        except Exception as e:
            raise CryptoError(
                f"Decryption failed: {e}",
                hint="Check your password. Wrong passwords will cause authentication failures.",
            ) from e

    # Decompress the gzipped tarball
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(decrypted_payload), mode="rb") as gz:
            return gz.read()
    except Exception as e:
        raise ArchiveError(
            f"Decompression failed: {e}",
            hint="The archive may be corrupted.",
        ) from e
