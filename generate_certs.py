#!/usr/bin/env python3
"""
Generates a self-signed SSL certificate for local/dev HTTPS.
For production, replace with a real cert from Let's Encrypt.

Run once:
    python generate_certs.py
"""
import os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta, timezone

os.makedirs("certs", exist_ok=True)

# Generate key
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Self-signed cert
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AuditBot Dev"),
    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
])

cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.now(timezone.utc))
    .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
    .add_extension(x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.IPAddress(__import__("ipaddress").IPv4Address("127.0.0.1")),
    ]), critical=False)
    .sign(key, hashes.SHA256())
)

with open("certs/key.pem", "wb") as f:
    f.write(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))

with open("certs/cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("✓  certs/cert.pem")
print("✓  certs/key.pem")
print("\nFor production: replace with Let's Encrypt certs")