from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # Formulario estándar de Swagger
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.core import security

router = APIRouter()

@router.post("/login", response_model=None) # Retorna un JSON custom
def login_access_token(
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # 1. Buscar usuario por email (username en el form)
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    # 2. Validar usuario y contraseña
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    # 3. Crear Token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id_usuario), "rol": user.rol.nombre}, # Guardamos ID y Rol en el token
        expires_delta=access_token_expires,
    )

    # 4. Devolver respuesta estándar OAuth2
    # Además devolvemos datos del usuario para que React sepa quién es
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id_usuario,
        "email": user.email,
        "rol": user.rol.nombre
    }