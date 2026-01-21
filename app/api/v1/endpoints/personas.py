# Archivo: app/api/v1/endpoints/personas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.schemas import persona_schema as schemas
from app.services.persona_service import PersonaService, PersonaNotFoundError
# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ESCRITURA, ROLES_ADMIN

def get_persona_service(db: Session = Depends(get_db)) -> PersonaService:
    return PersonaService(db)

router = APIRouter(
    prefix="/personas",
    tags=["Personas (Clientes, Administradores)"]
)

# 1. CREAR Persona (Escritura)
@router.post("/", response_model=schemas.Persona, status_code=status.HTTP_201_CREATED)
def create_persona_endpoint(
    persona: schemas.PersonaCreate, 
    servicio: PersonaService = Depends(get_persona_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Crea un nuevo registro de Persona."""
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="No tiene permisos para crear personas.")
         
    return servicio.create_persona(persona)

# 2. OBTENER Persona por ID (Lectura)
@router.get("/{persona_id}", response_model=schemas.Persona)
def read_persona_endpoint(
    persona_id: int, 
    servicio: PersonaService = Depends(get_persona_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    db_persona = servicio.get_persona_by_id(persona_id=persona_id)
    if db_persona is None:
        raise HTTPException(status_code=404, detail=f"Persona con ID {persona_id} no encontrada")
    return db_persona

# 3. LISTAR Personas (Lectura)
@router.get("/", response_model=List[schemas.Persona])
def read_personas_endpoint(
    skip: int = 0,
    limit: int = 100,
    servicio: PersonaService = Depends(get_persona_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return servicio.get_all_personas(skip=skip, limit=limit)

# 4. BÚSQUEDA AVANZADA (Lectura)
@router.get("/filter/", response_model=List[schemas.Persona])
def filter_personas_endpoint(
    filters: schemas.PersonaFilter = Depends(), 
    servicio: PersonaService = Depends(get_persona_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return servicio.get_filtered_personas(filters)

# 5. ACTUALIZAR Persona (Escritura)
@router.patch("/{persona_id}", response_model=schemas.Persona)
def update_persona_endpoint(
    persona_id: int,
    persona_in: schemas.PersonaUpdate,
    servicio: PersonaService = Depends(get_persona_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Actualiza los datos de una Persona."""
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="No tiene permisos para editar personas.")
         
    try:
        return servicio.update_persona(persona_id, persona_in)
    except PersonaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

# 6. ELIMINACIÓN LÓGICA (Administración)
@router.delete("/{persona_id}", response_model=schemas.Persona)
def soft_delete_persona_endpoint(
    persona_id: int,
    servicio: PersonaService = Depends(get_persona_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Baja lógica de Persona. Solo Admins."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo Administradores pueden dar de baja personas.")
         
    try:
        return servicio.soft_delete_persona(persona_id)
    except PersonaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))