"""
Encryption utilities for vote privacy.
Uses Fernet (symmetric encryption) for vote data.
Each question gets its own encryption key that only designated admins have.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import os


def generate_encryption_key(question_id: str, salt: bytes = None) -> tuple:
    """
    Generate an encryption key for a question.
    Returns (key, salt) - both should be stored/distributed to authorized admins.
    
    Args:
        question_id: The UUID of the question
        salt: Optional salt (if None, a new one is generated)
    
    Returns:
        Tuple of (encryption_key_base64, salt_base64)
    """
    if salt is None:
        salt = os.urandom(16)
    
    # Use PBKDF2 to derive a key from the question ID
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    # Derive key from question_id
    key = base64.urlsafe_b64encode(
        kdf.derive(question_id.encode())
    )
    
    salt_b64 = base64.urlsafe_b64encode(salt).decode()
    return key, salt_b64


def encrypt_vote(vote_answer: str, encryption_key: bytes) -> str:
    """
    Encrypt a vote answer.
    
    Args:
        vote_answer: The vote answer text (e.g., "Yes", "No")
        encryption_key: The encryption key (from generate_encryption_key or database)
    
    Returns:
        Encrypted vote as a UTF-8 string
    """
    f = Fernet(encryption_key)
    encrypted = f.encrypt(vote_answer.encode())
    return encrypted.decode()


def decrypt_vote(encrypted_vote: str, encryption_key: bytes) -> str:
    """
    Decrypt a vote answer.
    
    Args:
        encrypted_vote: The encrypted vote string from the database
        encryption_key: The encryption key (from database)
    
    Returns:
        Decrypted vote answer
    
    Raises:
        cryptography.fernet.InvalidToken: If the key is wrong or data is corrupted
    """
    f = Fernet(encryption_key)
    decrypted = f.decrypt(encrypted_vote.encode())
    return decrypted.decode()


def decrypt_votes_batch(encrypted_votes: list, encryption_key: bytes) -> list:
    """
    Decrypt multiple votes.
    
    Args:
        encrypted_votes: List of encrypted vote strings
        encryption_key: The encryption key
    
    Returns:
        List of decrypted vote answers
    """
    return [decrypt_vote(vote, encryption_key) for vote in encrypted_votes]
