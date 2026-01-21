from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas import medio_ingreso_schema as schemas
from app.services.medio_ingreso_service import MedioIngresoService
from app.db import models
# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ADMIN

router = APIRouter(
    prefix="/medios-ingreso",
    tags=["Medios de Ingreso"]
)

# Dependencia para inyectar el servicio
def get_service(db: Session = Depends(get_db)) -> MedioIngresoService:
    return MedioIngresoService(db)

# 1. CREAR (Solo Admin)
@router.post("/", response_model=schemas.MedioIngreso, status_code=status.HTTP_201_CREATED)
def create_medio_ingreso(
    medio_ingreso_in: schemas.MedioIngresoCreate,
    service: MedioIngresoService = Depends(get_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo administradores pueden configurar medios de pago.")
    return service.create(medio_ingreso_in)

# 2. LISTAR (Todos)
@router.get("/", response_model=List[schemas.MedioIngreso])
def read_medios_ingreso(
    skip: int = 0, 
    limit: int = 100, 
    service: MedioIngresoService = Depends(get_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
    return service.get_all(skip=skip, limit=limit)

# 3. LEER UNO (Todos)
@router.get("/{medio_ingreso_id}", response_model=schemas.MedioIngreso)
def read_medio_ingreso(
    medio_ingreso_id: int, 
    service: MedioIngresoService = Depends(get_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
    return service.get_by_id(medio_ingreso_id)

# 4. ACTUALIZAR (Solo Admin)
@router.put("/{medio_ingreso_id}", response_model=schemas.MedioIngreso)
def update_medio_ingreso_endpoint(
    medio_ingreso_id: int, 
    medio_ingreso_in: schemas.MedioIngresoUpdate, 
    service: MedioIngresoService = Depends(get_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para modificar medios de pago.")
    return service.update(medio_ingreso_id, medio_ingreso_in)

# 5. ELIMINAR (Solo Admin)
@router.delete("/{medio_ingreso_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medio_ingreso_endpoint(
    medio_ingreso_id: int, 
    service: MedioIngresoService = Depends(get_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para eliminar medios de pago.")
    service.delete(medio_ingreso_id)