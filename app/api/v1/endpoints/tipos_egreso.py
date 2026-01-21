from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

# Importaciones de la arquitectura
from app.db.database import get_db
from app.schemas import tipo_egreso_schema as schemas
from app.services.tipo_egreso_service import TipoEgresoService
from app.db import models
# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ADMIN

# ----------------------------------------------------
# DEFINICIÓN DE LA DEPENDENCIA PARA EL SERVICIO
# ----------------------------------------------------
def get_tipo_egreso_service(db: Session = Depends(get_db)) -> TipoEgresoService:
    return TipoEgresoService(db)

router = APIRouter(
    prefix="/tipos-egreso",
    tags=["Catálogo - Tipos de Egreso"]
)

# ----------------------------------------------------
# 1. CREAR (POST) - Solo Admin
# ----------------------------------------------------
@router.post("/", response_model=schemas.TipoEgreso, status_code=status.HTTP_201_CREATED)
def create_tipo_egreso_endpoint(
    tipo: schemas.TipoEgresoCreate,
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Crea un nuevo Tipo de Egreso (Ej: Luz, Agua, Mantenimiento)."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo administradores pueden crear tipos de egreso.")

    return servicio.create(tipo_in=tipo)

# ----------------------------------------------------
# 2. LEER/LISTAR (GET) - Todos
# ----------------------------------------------------
@router.get("/", response_model=List[schemas.TipoEgreso])
def read_tipos_egreso_endpoint(
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = Query(False, description="Incluir Tipos de Egreso inactivos."),
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Obtiene la lista de todos los Tipos de Egreso."""
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return servicio.get_all(skip=skip, limit=limit, include_inactive=include_inactive)

# ----------------------------------------------------
# 3. LEER POR ID (GET /{id}) - Todos
# ----------------------------------------------------
@router.get("/{tipo_egreso_id}", response_model=schemas.TipoEgreso)
def read_tipo_egreso_by_id_endpoint(
    tipo_egreso_id: int, 
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    return servicio.get_by_id(tipo_egreso_id=tipo_egreso_id)

# ----------------------------------------------------
# 4. ACTUALIZAR (PUT/PATCH) - Solo Admin
# ----------------------------------------------------
@router.put("/{tipo_egreso_id}", response_model=schemas.TipoEgreso)
def update_tipo_egreso_endpoint(
    tipo_egreso_id: int,
    tipo: schemas.TipoEgresoUpdate,
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Actualiza completamente un Tipo de Egreso existente."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para modificar tipos de egreso.")

    return servicio.update(tipo_egreso_id=tipo_egreso_id, tipo_in=tipo)

# ----------------------------------------------------
# 5. BORRADO SUAVE (DELETE) - Solo Admin
# ----------------------------------------------------
@router.delete("/{tipo_egreso_id}", response_model=schemas.TipoEgreso)
def soft_delete_tipo_egreso_endpoint(
    tipo_egreso_id: int,
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Desactiva lógicamente un Tipo de Egreso."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para eliminar tipos de egreso.")

    return servicio.soft_delete(tipo_egreso_id=tipo_egreso_id)

# ----------------------------------------------------
# 6. ACTIVAR (PATCH) - Solo Admin
# ----------------------------------------------------
@router.patch("/{tipo_egreso_id}/activate", response_model=schemas.TipoEgreso)
def activate_tipo_egreso_endpoint(
    tipo_egreso_id: int,
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Activa lógicamente un Tipo de Egreso que fue desactivado."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para reactivar tipos de egreso.")

    return servicio.activate(tipo_egreso_id=tipo_egreso_id)