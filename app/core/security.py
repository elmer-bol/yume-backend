from datetime import datetime, timedelta
from typing import Optional, Union
from jose import jwt # Librería python-jose
from passlib.context import CryptContext

# --- CONFIGURACIÓN DE SEGURIDAD ---
# En producción, esto debería venir de variables de entorno (.env)
SECRET_KEY = "ESTA_ES_LA_CLAVE_SECRETA_DEL_ERP_INMOBILIARIO_CAMBIAME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480 # 8 horas de sesión

# Configuración de Hashing (IGUAL QUE EN POPULATE_DB)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verifica si la contraseña escrita coincide con el hash de la BD."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Genera el hash para guardar en BD (usado al crear usuarios)."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Genera el Token JWT que enviaremos al Frontend."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Agregamos la fecha de expiración al token
    to_encode.update({"exp": expire})
    
    # Firmamos digitalmente
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt