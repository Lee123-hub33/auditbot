#!/usr/bin/env python3
"""
Run once before first start:
    python generate_keys.py

Generates RSA-2048 keypair for JWT RS256 signing.
Keys are saved to ./secrets/ (git-ignored).
"""

import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

os.makedirs("secrets", exist_ok=True)

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Write private key
with open("secrets/jwt_private.pem", "wb") as f:
    f.write(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

# Write public key
with open("secrets/jwt_public.pem", "wb") as f:
    f.write(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

print("✓  secrets/jwt_private.pem")
print("✓  secrets/jwt_public.pem")
print("\nDone. Keys are git-ignored. Back them up securely.")
