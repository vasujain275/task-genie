import hmac
import hashlib
import json
from urllib.parse import parse_qs, unquote
from fastapi import HTTPException
from datetime import datetime
from app.config import settings
from cryptography.fernet import Fernet, InvalidToken
from typing import Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# ============= TELEGRAM WEB APP AUTHENTICATION =============


def verify_telegram_webapp_data(init_data: str) -> dict:
    """
    Verifies Telegram Web App data is authentic and not tampered with.
    Returns the user data if valid, raises HTTPException if invalid.

    This prevents attackers from:
    1. Spoofing URLs with different telegram_ids
    2. Modifying other users' credentials
    3. Creating fake authentication requests
    """
    try:
        logger.debug("Verifying Telegram webapp data")
        # Parse the init_data string
        parsed_data = parse_qs(init_data)

        # Extract and remove hash
        received_hash = parsed_data.get("hash", [""])[0]
        if not received_hash:
            logger.warning("No hash provided in webapp data")
            raise ValueError("No hash provided")

        # Remove hash from data for verification
        data_check_dict = {k: v[0] for k, v in parsed_data.items() if k != "hash"}

        # Create data-check-string (sorted key=value pairs)
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(data_check_dict.items())
        )

        # Calculate expected hash
        secret_key = hmac.new(
            key="WebAppData".encode(),
            msg=settings.TELEGRAM_BOT_TOKEN.encode(),
            digestmod=hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key, msg=data_check_string.encode(), digestmod=hashlib.sha256
        ).hexdigest()

        # Verify hash matches
        if not hmac.compare_digest(received_hash, calculated_hash):
            logger.warning("Webapp data hash verification failed")
            raise ValueError("Hash verification failed")

        # Check auth_date is recent (within 24 hours)
        auth_date = int(data_check_dict.get("auth_date", 0))
        if datetime.now().timestamp() - auth_date > 86400:  # 24 hours
            logger.warning("Webapp authentication data is too old")
            raise ValueError("Authentication data is too old")

        # Parse user data
        user_data = json.loads(unquote(data_check_dict.get("user", "{}")))

        logger.info(
            f"Webapp data verified successfully for user: {user_data.get('id')}"
        )

        return {
            "telegram_id": user_data.get("id"),
            "first_name": user_data.get("first_name"),
            "username": user_data.get("username"),
            "auth_date": auth_date,
        }

    except Exception as e:
        logger.error(f"Telegram authentication failed: {e}")
        raise HTTPException(
            status_code=401, detail=f"Invalid Telegram authentication: {str(e)}"
        )


# ============= API KEY ENCRYPTION =============
# Generate and store this key securely (environment variable)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY = settings.ENCRYPTION_KEY


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypts an API key before storing in database.

    Args:
        api_key: The plaintext API key (e.g., OpenAI, Gemini key)

    Returns:
        Encrypted string safe to store in database

    Raises:
        ValueError: If encryption key not set or API key is empty
    """
    if not ENCRYPTION_KEY:
        logger.error("ENCRYPTION_KEY not set in environment")
        raise ValueError("ENCRYPTION_KEY not set in environment variables")

    if not api_key or not api_key.strip():
        logger.warning("Attempt to encrypt empty API key")
        raise ValueError("API key cannot be empty")

    try:
        # Create Fernet cipher instance with your encryption key
        f = Fernet(ENCRYPTION_KEY)

        # Encrypt the API key
        encrypted = f.encrypt(api_key.encode())

        # Return as string (Fernet returns bytes, we convert to string for MongoDB)
        logger.debug("API key encrypted successfully")
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {e}")
        raise


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """
    Decrypts an API key when needed for making API calls.

    Args:
        encrypted_key: The encrypted key from database

    Returns:
        The original plaintext API key

    Raises:
        ValueError: If encryption key not set or decryption fails
    """
    if not ENCRYPTION_KEY:
        logger.error("ENCRYPTION_KEY not set in environment")
        raise ValueError("ENCRYPTION_KEY not set in environment variables")

    try:
        # Create Fernet cipher instance with your encryption key
        f = Fernet(ENCRYPTION_KEY)

        # Decrypt the API key
        decrypted = f.decrypt(encrypted_key.encode())

        # Return as string
        logger.debug("API key decrypted successfully")
        return decrypted.decode()

    except InvalidToken:
        # This happens if key was tampered with or wrong encryption key used
        logger.error("Failed to decrypt API key - invalid or corrupted data")
        raise ValueError("Failed to decrypt API key - invalid or corrupted data")
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        raise
