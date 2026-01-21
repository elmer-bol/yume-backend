# Archivo: app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Variables obligatorias
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    SECRET_KEY: str

    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "Sistema de Cobros YUME"

    # --- NUEVA VARIABLE: DURACIÓN DE SESIÓN ---
    # 60 minutos * 8 horas = 480 minutos.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding='utf-8',
        extra='ignore' 
    )

settings = Settings()

# --- CONSTANTES DE SEGURIDAD Y ROLES ---
# Estas no van dentro de Settings porque no se cargan desde el .env,
# son reglas fijas del negocio.

# Nivel 1: Ver datos (Lectura)
ROLES_LECTURA = ["SuperAdmin", "AdminEdif", "Cajero", "Visual"]

# Nivel 2: Operar (Crear/Editar)
ROLES_ESCRITURA = ["SuperAdmin", "AdminEdif", "Cajero"]

# Nivel 3: Gestión Crítica (Anular/Eliminar)
ROLES_ADMIN = ["SuperAdmin", "AdminEdif"]