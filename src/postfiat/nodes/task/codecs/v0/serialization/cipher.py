import base64
import hashlib
from cryptography.fernet import Fernet
from nacl.bindings import (
    crypto_sign_ed25519_pk_to_curve25519,
    crypto_sign_ed25519_sk_to_curve25519,
    crypto_scalarmult,
)

from postfiat.models.transaction import Transaction

PREFIX = 'WHISPER__'


def derive_shared_secret(pubkey_hex: str, secret_hex: str) -> str:
    pubkey_raw: bytes = bytes.fromhex(pubkey_hex[2:])
    secret_raw: bytes = bytes.fromhex(secret_hex[2:])
    assert len(pubkey_raw) == 32 and len(secret_raw) == 32

    x25519_pubkey = crypto_sign_ed25519_pk_to_curve25519(pubkey_raw)
    x25519_secret = crypto_sign_ed25519_sk_to_curve25519(secret_raw + pubkey_raw)

    return crypto_scalarmult(x25519_secret, x25519_pubkey)


def derive_symmetric_cryptor(pubkey_hex: str, secret_hex: str) -> Fernet:
    shared_secret = derive_shared_secret(pubkey_hex, secret_hex)
    return Fernet(
        base64.urlsafe_b64encode(hashlib.sha256(shared_secret).digest()))


def encrypt_memo(memo_data: str, pubkey: str, secret: str) -> str:
    cryptor = derive_symmetric_cryptor(pubkey, secret)
    return PREFIX + cryptor.encrypt(memo_data.encode()).decode()


def decrypt_memo(memo_data: str, pubkey: str, secret: str) -> str:
    cryptor = derive_symmetric_cryptor(pubkey, secret)
    if memo_data.startswith(PREFIX):
        memo_data = memo_data[len(PREFIX):]
    return cryptor.decrypt(memo_data.encode()).decode()


def encrypt_txn(txn: Transaction, pubkey: str, secret: str) -> Transaction:
    memo_data = encrypt_memo(txn.memo_data, pubkey, secret)
    return txn.model_copy(update={'memo_data': memo_data})


def decrypt_txn(txn: Transaction, pubkey: str, secret: str) -> Transaction:
    memo_data = decrypt_memo(txn.memo_data, pubkey, secret)
    return txn.model_copy(update={'memo_data': memo_data})


def is_memo_encrypted(memo_data: str) -> bool:
    return memo_data.startswith(PREFIX)


def is_txn_encrypted(txn: Transaction) -> bool:
    return is_memo_encrypted(txn.memo_data)
