import os
from typing import Optional
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Debug: verificar se o arquivo .env foi carregado
import os
env_file_path = os.path.join(os.getcwd(), '.env')
print(f"🔧 Verificando arquivo .env: {env_file_path}")
print(f"🔧 Arquivo .env existe: {os.path.exists(env_file_path)}")
if os.path.exists(env_file_path):
    with open(env_file_path, 'r') as f:
        content = f.read()
        print(f"🔧 Conteúdo do .env (primeiras 200 chars): {content[:200]}")

class Settings(BaseSettings):
    # API Keys
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")
    WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL")
    
    # Security
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "your-secret-key-change-in-production-min-32-chars")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-change-in-production-min-32-chars")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
    RATE_LIMIT_MINUTES: int = int(os.getenv("RATE_LIMIT_MINUTES", "1"))
    MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    
    # File handling
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
    ALLOWED_EXTENSIONS: str = os.getenv("ALLOWED_EXTENSIONS", "mp4,avi,mov,mkv,mp3,wav,m4a")
    
    @field_validator("ASSEMBLYAI_API_KEY")
    @classmethod
    def validate_assemblyai_key(cls, v):
        if not v or v == "":
            # Em desenvolvimento, usar chave padrão se não configurada
            import os
            if os.getenv("ENVIRONMENT", "development") == "development":
                return "245ef4a0549d4808bb382cd40d9c054d"  # Chave de desenvolvimento
            raise ValueError("ASSEMBLYAI_API_KEY é obrigatória em produção")
        return v
    
    @field_validator("API_SECRET_KEY", "JWT_SECRET_KEY")
    @classmethod
    def validate_secret_keys(cls, v):
        if len(v) < 32:
            raise ValueError("Secret keys devem ter pelo menos 32 caracteres")
        return v
    
    @property
    def allowed_extensions_list(self) -> list:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instância global das configurações
settings = Settings()