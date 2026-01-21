from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.schemas import unidad_servicio_schema as schemas
from app.services.unidad_servicio_service import UnidadServicioService

# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ESCRITURA, ROLES_ADMIN

def get_unidad_servicio_service(db: Session = Depends(get_db)) -> UnidadServicioService:
    return UnidadServicioService(db)

router = APIRouter(
    prefix="/unidades",
    tags=["Unidades de Servicio (Universal)"]
)

# ----------------------------------------------------
# 1. CREACIÓN (POST /unidades/)
# ----------------------------------------------------
@router.post("/", response_model=schemas.UnidadServicio, status_code=status.HTTP_201_CREATED)
def create_unidad_endpoint(
    unidad: schemas.UnidadServicioCreate, 
    servicio: UnidadServicioService = Depends(get_unidad_servicio_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    # 1. PRIMERO: SEGURIDAD
    if current_user.rol.nombre not in ROLES_ESCRITURA:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear unidades de servicio.")       

    # 2. LUEGO: LÓGICA
    db_unidad = servicio.create_unidad(unidad)
    
    if db_unidad is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="El identificador único de la Unidad de Servicio ya existe."
        )
    
    return db_unidad

# ----------------------------------------------------
# 2. LECTURA POR ID (GET /unidades/{unidad_id})
# ----------------------------------------------------
@router.get("/{unidad_id}", response_model=schemas.UnidadServicio)
def read_unidad_endpoint(
    unidad_id: int, 
    servicio: UnidadServicioService = Depends(get_unidad_servicio_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
    
    db_unidad = servicio.get_unidad_by_id(unidad_id=unidad_id)
    if db_unidad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad de Servicio no encontrada")

    return db_unidad

# ----------------------------------------------------
# 3. LECTURA / BÚSQUEDA CON FILTROS (GET /unidades/)
# ----------------------------------------------------
@router.get("/", response_model=List[schemas.UnidadServicio])
def read_unidades_with_filters(
    skip: int = 0, 
    limit: int = 500, 
    filters: schemas.UnidadServicioFilter = Depends(), 
    servicio: UnidadServicioService = Depends(get_unidad_servicio_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
    
    if filters.is_empty(): 
        unidades = servicio.get_all_unidades(skip=skip, limit=limit)
    else:
        unidades = servicio.search_unidades(filters=filters, skip=skip, limit=limit)
        
    return unidades

# ----------------------------------------------------
# 4. ACTUALIZACIÓN (PUT /unidades/{unidad_id})
# ----------------------------------------------------
@router.put("/{unidad_id}", response_model=schemas.UnidadServicio)
def update_unidad_endpoint(
    unidad_id: int, 
    unidad: schemas.UnidadServicioUpdate,
    servicio: UnidadServicioService = Depends(get_unidad_servicio_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="No tiene permisos para editar unidades de servicio.")
    
    db_unidad = servicio.update_unidad(unidad_id=unidad_id, unidad_in=unidad)
    
    if db_unidad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad de Servicio no encontrada")
        
    return db_unidad

# ----------------------------------------------------
# 5. ELIMINACIÓN LÓGICA (DELETE /unidades/{unidad_id})
# ----------------------------------------------------
@router.delete("/{unidad_id}", response_model=schemas.UnidadServicio)
def delete_unidad_endpoint(
    unidad_id: int, 
    servicio: UnidadServicioService = Depends(get_unidad_servicio_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Aquí usamos ROLES_ADMIN, es correcto que sea más estricto
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo Administradores pueden dar de baja unidades de servicio.")
    
    db_unidad = servicio.soft_delete_unidad(unidad_id=unidad_id)
    
    if db_unidad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad de Servicio no encontrada")
        
    return db_unidad