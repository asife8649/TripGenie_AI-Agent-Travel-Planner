import os

from datetime import (
    datetime,
    timedelta,
    timezone
)

import bcrypt

from jose import (
    JWTError,
    jwt
)

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# JWT CONFIGURATION
# ============================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY"
)

if not SECRET_KEY:

    raise ValueError(
        "SECRET_KEY is not set in backend/.env"
    )


ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


# ============================================================
# PASSWORD HASH
# ============================================================

def hash_password(
    password: str
) -> str:

    password_bytes = (
        password.encode("utf-8")
    )

    if len(password_bytes) > 72:

        raise ValueError(
            "Password must be 72 bytes or less"
        )

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode(
        "utf-8"
    )


# ============================================================
# VERIFY PASSWORD
# ============================================================

def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    password_bytes = (
        plain_password.encode("utf-8")
    )

    if len(password_bytes) > 72:

        return False

    try:

        return bcrypt.checkpw(
            password_bytes,
            hashed_password.encode(
                "utf-8"
            )
        )

    except Exception:

        return False


# ============================================================
# CREATE JWT
# ============================================================

def create_access_token(
    data: dict,
    expires_delta:
        timedelta | None = None
) -> str:

    to_encode = data.copy()

    if expires_delta:

        expire = (
            datetime.now(
                timezone.utc
            )
            + expires_delta
        )

    else:

        expire = (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                minutes=
                    ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )

    to_encode["exp"] = expire

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ============================================================
# DECODE JWT
# ============================================================

def decode_access_token(
    token: str
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[
                ALGORITHM
            ]
        )

        return payload

    except JWTError:

        return None