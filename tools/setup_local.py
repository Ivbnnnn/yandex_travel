"""Create local development keys/config without replacing existing files."""

import secrets
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def prepare_key_pair(directory: Path, name: str) -> None:
    private_path = directory / f"{name}-private.pem"
    public_path = directory / f"{name}-public.pem"
    if private_path.exists():
        private = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    else:
        if public_path.exists():
            raise RuntimeError(f"Public key exists without private key: {public_path}")
        private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        private_path.write_bytes(
            private.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        private_path.chmod(0o600)
    public_bytes = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    if public_path.exists():
        if public_path.read_bytes() != public_bytes:
            raise RuntimeError(f"Key pair does not match: {public_path}")
    else:
        public_path.write_bytes(public_bytes)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    keys = root / ".local" / "keys"
    keys.mkdir(parents=True, exist_ok=True)
    for name in ("auth", "gateway"):
        prepare_key_pair(keys, name)
    env_path = root / ".env.local"
    if not env_path.exists():
        template = (root / ".env.example").read_text(encoding="utf-8")
        template = template.replace(
            "replace-this-with-at-least-32-random-characters", secrets.token_urlsafe(48)
        ).replace("local-user-service-password", secrets.token_hex(20))
        env_path.write_text(template, encoding="utf-8")
    print("Local keys and .env.local are ready; existing files were preserved.")


if __name__ == "__main__":
    main()
