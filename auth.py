from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings
import logging

logger = logging.getLogger(__name__)

# Configuração de hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuração de autenticação
security = HTTPBearer()

# Usuários hardcoded para demonstração - em produção usar banco de dados
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),  # Senha: admin123
        "is_active": True,
        "scopes": ["transcribe", "admin"]
    },
    "user": {
        "username": "user",
        "hashed_password": pwd_context.hash("user123"),   # Senha: user123
        "is_active": True,
        "scopes": ["transcribe"]
    }
}

class AuthManager:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica se a senha está correta"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Gera hash da senha"""
        return pwd_context.hash(password)
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
        """Autentica usuário"""
        user = DEMO_USERS.get(username)
        if not user:
            return None
        if not AuthManager.verify_password(password, user["hashed_password"]):
            return None
        return user
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Cria token JWT"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verifica e decodifica token JWT"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            
            # Verificar se usuário ainda existe e está ativo
            user = DEMO_USERS.get(username)
            if user and user.get("is_active", False):
                return {"username": username, "scopes": user.get("scopes", [])}
            return None
            
        except JWTError as e:
            logger.warning(f"Token JWT inválido: {e}")
            return None

# Dependências para autenticação
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency para obter usuário atual autenticado"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    user = AuthManager.verify_token(credentials.credentials)
    if user is None:
        logger.warning(f"Tentativa de acesso com token inválido")
        raise credentials_exception
    
    logger.info(f"Usuário autenticado: {user['username']}")
    return user

async def require_scope(required_scope: str):
    """Factory para criar dependency que requer scope específico"""
    async def check_scope(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if required_scope not in current_user.get("scopes", []):
            logger.warning(f"Usuário {current_user['username']} não tem permissão '{required_scope}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão insuficiente. Requer: {required_scope}"
            )
        return current_user
    return check_scope

# Funções utilitárias
def generate_api_key() -> str:
    """Gera uma chave API segura"""
    return secrets.token_urlsafe(32)

def validate_api_key(api_key: str) -> bool:
    """Valida chave API (implementação básica)"""
    # Em produção, armazenar chaves em banco de dados
    return api_key == settings.API_SECRET_KEY