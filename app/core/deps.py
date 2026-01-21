from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.core import security

# Indica a FastAPI que el token viene del endpoint "/v1/login"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Usuario:
    """
    Dependencia que valida el token y devuelve el usuario actual.
    Si el token es falso o expiró, lanza error 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificamos el token
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        
        # Extraemos el ID del usuario (lo guardaremos como 'sub' en el token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Buscamos al usuario en la BD
    user = db.query(models.Usuario).filter(models.Usuario.id_usuario == user_id).first()
    
    if user is None:
        raise credentials_exception
        
    if not user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
        
    return user