"""Authentication service for QLP"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import User, Organization, APIKey, UserRole
from src.common.config import settings
from src.common.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for authentication and authorization"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.secret_key = settings.SECRET_KEY or "your-secret-key-here"
        self.algorithm = "HS256"
        self.token_expiry_hours = 24
    
    async def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        organization_name: Optional[str] = None
    ) -> Tuple[User, Organization]:
        """Register a new user and optionally create organization"""
        
        # Check if user exists
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("User with this email already exists")
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create organization if needed
        if organization_name:
            org = Organization(
                name=organization_name,
                slug=self._generate_slug(organization_name)
            )
            self.db.add(org)
            await self.db.flush()  # Get org.id
        else:
            # Find or create personal organization
            org = Organization(
                name=f"{full_name}'s Workspace",
                slug=self._generate_slug(email.split('@')[0])
            )
            self.db.add(org)
            await self.db.flush()
        
        # Create user
        user = User(
            email=email,
            password_hash=password_hash.decode('utf-8'),
            full_name=full_name,
            organization_id=org.id,
            role=UserRole.OWNER  # First user is owner
        )
        self.db.add(user)
        
        await self.db.commit()
        
        logger.info(
            "User registered",
            user_id=str(user.id),
            organization_id=str(org.id)
        )
        
        return user, org
    
    async def login(
        self,
        email: str,
        password: str
    ) -> Tuple[User, str]:
        """Authenticate user and return JWT token"""
        
        # Find user
        stmt = select(User).where(User.email == email, User.is_active == True)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Invalid credentials")
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise ValueError("Invalid credentials")
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()
        
        # Generate token
        token = self.create_token(user)
        
        logger.info("User logged in", user_id=str(user.id))
        
        return user, token
    
    def create_token(self, user: User) -> str:
        """Create JWT token for user"""
        
        payload = {
            "user_id": str(user.id),
            "organization_id": str(user.organization_id),
            "email": user.email,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token"""
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    async def create_api_key(
        self,
        user_id: UUID,
        name: str,
        scopes: list = None,
        expires_in_days: Optional[int] = None
    ) -> Tuple[APIKey, str]:
        """Create API key for user"""
        
        # Generate key
        raw_key = f"qlp_{secrets.token_urlsafe(32)}"
        key_hash = bcrypt.hashpw(raw_key.encode('utf-8'), bcrypt.gensalt())
        
        # Create API key record
        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash.decode('utf-8'),
            key_prefix=raw_key[:10],
            scopes=scopes or ["read", "write"],
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        )
        
        self.db.add(api_key)
        await self.db.commit()
        
        logger.info(
            "API key created",
            user_id=str(user_id),
            key_id=str(api_key.id),
            prefix=api_key.key_prefix
        )
        
        return api_key, raw_key
    
    async def verify_api_key(self, key: str) -> Tuple[User, APIKey]:
        """Verify API key and return user"""
        
        if not key.startswith("qlp_"):
            raise ValueError("Invalid API key format")
        
        # Find by prefix
        prefix = key[:10]
        stmt = select(APIKey).where(
            APIKey.key_prefix == prefix,
            APIKey.is_active == True
        )
        result = await self.db.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise ValueError("Invalid API key")
        
        # Check expiry
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            raise ValueError("API key has expired")
        
        # Verify full key
        if not bcrypt.checkpw(key.encode('utf-8'), api_key.key_hash.encode('utf-8')):
            raise ValueError("Invalid API key")
        
        # Update last used
        api_key.last_used_at = datetime.utcnow()
        
        # Get user
        user = await self.db.get(User, api_key.user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")
        
        await self.db.commit()
        
        return user, api_key
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL-safe slug from name"""
        
        slug = name.lower()
        slug = ''.join(c if c.isalnum() else '-' for c in slug)
        slug = '-'.join(filter(None, slug.split('-')))
        
        # Add random suffix to ensure uniqueness
        suffix = secrets.token_hex(3)
        return f"{slug}-{suffix}"