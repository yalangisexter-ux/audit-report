"""Tests for secure verification of downloaded GitHub release installers."""
import hashlib

import pytest

import app


def test_release_asset_checksum_accepts_matching_sha256():
    data = b"trusted installer payload"
    asset = {"digest": "sha256:" + hashlib.sha256(data).hexdigest()}
    assert app.verify_release_asset_bytes(data, asset) is True


def test_release_asset_checksum_rejects_modified_payload():
    asset = {"digest": "sha256:" + hashlib.sha256(b"original").hexdigest()}
    with pytest.raises(ValueError, match="checksum verification failed"):
        app.verify_release_asset_bytes(b"modified", asset)


def test_release_asset_requires_digest_for_updates():
    with pytest.raises(ValueError, match="no SHA-256 digest"):
        app.verify_release_asset_bytes(b"payload", {}, require_digest=True)


def test_legacy_rollback_asset_can_be_used_without_digest():
    # Older releases may not expose digest metadata; size and trusted HTTPS URL
    # are checked by the rollback flow before this helper is called.
    assert app.verify_release_asset_bytes(b"legacy payload", {}, require_digest=False) is False


def test_release_asset_rejects_malformed_digest():
    with pytest.raises(ValueError, match="invalid SHA-256 digest"):
        app.verify_release_asset_bytes(b"payload", {"digest": "md5:abc"})
