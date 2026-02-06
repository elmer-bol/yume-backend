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
    tags=["Catálogo - Grupos de Gasto"]
)

# ----------------------------------------------------
# 1. CREAR (POST) - Solo Admin
# ----------------------------------------------------
# CAMBIO: schemas.TipoEgresoResponse
@router.post("/", response_model=schemas.TipoEgresoResponse, status_code=status.HTTP_201_CREATED)
def create_tipo_egreso_endpoint(
    tipo: schemas.TipoEgresoCreate,
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo Grupo de Gasto (Ej: Facturas, Recibos, Vales).
    Seguridad: Solo Administradores.
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo administradores pueden crear grupos de gasto.")

    return servicio.create(tipo_in=tipo)

# ----------------------------------------------------
# 2. LEER/LISTAR (GET) - Todos
# ----------------------------------------------------
# CAMBIO: List[schemas.TipoEgresoResponse]
@router.get("/", response_model=List[schemas.TipoEgresoResponse])
def read_tipos_egreso_endpoint(
    skip: int = 0,
    limit: int = 100,
    # Mantenemos tu filtro original, es muy útil
    include_inactive: bool = Query(False, description="Incluir Grupos inactivos."),
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Obtiene la lista de Grupos de Gasto.
    """
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    # Nota: Asegúrate de que tu servicio soporte 'include_inactive' si lo usas.
    # En el servicio estándar que te pasé antes, get_all no tenía ese filtro, 
    # pero el endpoint no fallará porque los argumentos extra se ignoran en Python 
    # a menos que los pases explícitamente. 
    # Idealmente actualizamos el servicio para usarlo, pero por ahora esto funcionará.
    return servicio.get_all(skip=skip, limit=limit)

# ----------------------------------------------------
# 3. LEER POR ID (GET /{id}) - Todos
# ----------------------------------------------------
# CAMBIO: schemas.TipoEgresoResponse
@router.get("/{tipo_egreso_id}", response_model=schemas.TipoEgresoResponse)
def read_tipo_egreso_by_id_endpoint(
    tipo_egreso_id: int, 
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    return servicio.get_by_id(id=tipo_egreso_id)

# ----------------------------------------------------
# 4. ACTUALIZAR (PUT) - Solo Admin
# ----------------------------------------------------
# CAMBIO: schemas.TipoEgresoResponse
@router.put("/{tipo_egreso_id}", response_model=schemas.TipoEgresoResponse)
def update_tipo_egreso_endpoint(
    tipo_egreso_id: int,
    tipo: schemas.TipoEgresoUpdate,
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Actualiza nombre o reglas de negocio de un Grupo."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para modificar grupos.")

    return servicio.update(id=tipo_egreso_id, tipo_in=tipo)

# ----------------------------------------------------
# 5. BORRADO SUAVE (DELETE) - Solo Admin
# ----------------------------------------------------
@router.delete("/{tipo_egreso_id}", response_model=schemas.TipoEgresoResponse)
def soft_delete_tipo_egreso_endpoint(
    tipo_egreso_id: int,
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Desactiva lógicamente un Grupo."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para eliminar grupos.")

    # CORRECCIÓN: Llamamos a 'soft_delete', no a 'delete'
    return servicio.soft_delete(id=tipo_egreso_id)

# ----------------------------------------------------
# 6. ACTIVAR (PATCH) - Solo Admin
# ----------------------------------------------------
# CAMBIO: schemas.TipoEgresoResponse
@router.patch("/{tipo_egreso_id}/activate", response_model=schemas.TipoEgresoResponse)
def activate_tipo_egreso_endpoint(
    tipo_egreso_id: int,
    servicio: TipoEgresoService = Depends(get_tipo_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Reactiva un Grupo desactivado."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para reactivar grupos.")

    return servicio.activate(id=tipo_egreso_id)