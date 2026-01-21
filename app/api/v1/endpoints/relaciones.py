# Archivo: app/api/v1/endpoints/relaciones.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db import models
from app.schemas import relacion_cliente_schema as schemas
from app.services.relacion_cliente_service import RelacionClienteService, NotFoundError # Importamos la excepción

# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ESCRITURA, ROLES_ADMIN

# ----------------------------------------------------
# DEFINICIÓN DE LA DEPENDENCIA DEL SERVICIO
# ----------------------------------------------------
def get_relacion_cliente_service(db: Session = Depends(get_db)) -> RelacionClienteService:
    """Dependencia que inicializa y provee la instancia de RelacionClienteService."""
    return RelacionClienteService(db)
    
router = APIRouter(
    prefix="/relaciones",
    tags=["Relaciones Cliente-Servicio"]
)

# ----------------------------------------------------
# 1. POST (CREAR)
# ----------------------------------------------------
@router.post(
    "/",  
    response_model=schemas.RelacionCliente,  
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva Relación Cliente-Servicio"
)
def create_relacion_endpoint(
    relacion: schemas.RelacionClienteCreate, 
    servicio: RelacionClienteService = Depends(get_relacion_cliente_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Crea una nueva Relación Cliente-Unidad de Servicio.
    Verifica que el ID de Persona y el ID de Unidad de Servicio existan.    
    """
    if current_user.rol.nombre not in ROLES_ESCRITURA:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear relación")   

    try:
        return servicio.create_relacion(relacion)
    except NotFoundError as e:
        # Captura NotFoundError si Persona o Unidad no existen (lógica de negocio)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al crear relación: {e}")

# ----------------------------------------------------
# 2. GET (OBTENER POR ID)
# ----------------------------------------------------
@router.get(
    "/{relacion_id}", 
    response_model=schemas.RelacionCliente,
    summary="Obtiene una Relación por su ID"
)
def read_relacion_endpoint(
    relacion_id: int, 
    servicio: RelacionClienteService = Depends(get_relacion_cliente_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
    """Obtiene una Relación Cliente-Servicio específica por su ID único."""
    try:
        db_relacion = servicio.get_relacion_by_id(relacion_id=relacion_id)
        return db_relacion
    except NotFoundError as e:
        # Captura NotFoundError si la relación no existe
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# ----------------------------------------------------
# 3. GET (LISTAR Y FILTRAR)
# ----------------------------------------------------
@router.get(
    "/", 
    response_model=List[schemas.RelacionCliente],
    summary="Lista todas las Relaciones, con filtros dinámicos"
)
def read_relaciones_endpoint(
    # Filtros dinámicos inyectados como query parameters (FastAPI lo hace automáticamente)
    filtros: schemas.RelacionClienteFilter = Depends(), 
    # Paginación (opcional)
    skip: int = Query(0, description="Número de registros a omitir (offset)."),  
    limit: int = Query(100, description="Límite de registros a devolver."),  
    servicio: RelacionClienteService = Depends(get_relacion_cliente_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
    """
    Obtiene una lista paginada de todas las Relaciones. 
    Permite filtrar por id_persona, id_unidad, estado, tipo_relacion y rango de fechas.
    """
    # La funcionalidad del endpoint /persona/{persona_id} ahora está cubierta aquí:
    # Ejemplo: GET /relaciones?id_persona=123
    relaciones = servicio.get_all_relaciones(filtros=filtros, skip=skip, limit=limit)
    return relaciones

# ----------------------------------------------------
# 4. PATCH (ACTUALIZAR PARCIALMENTE)
# ----------------------------------------------------
@router.patch(
    "/{relacion_id}", 
    response_model=schemas.RelacionCliente,
    summary="Actualiza campos específicos de una Relación"
)
def update_relacion_endpoint(
    relacion_id: int,
    relacion_update: schemas.RelacionClienteUpdate, 
    servicio: RelacionClienteService = Depends(get_relacion_cliente_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Actualiza uno o varios campos de una Relación Cliente-Servicio existente.
    """
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="No tiene permisos para editar relación.")
    try:
        return servicio.update_relacion(relacion_id=relacion_id, relacion_update=relacion_update)
    except NotFoundError as e:
        # Captura NotFoundError si la relación o los IDs referenciados no existen
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al actualizar relación: {e}")

# ----------------------------------------------------
# 5. DELETE (BORRADO LÓGICO)
# ----------------------------------------------------
@router.delete(
    "/{relacion_id}", 
    response_model=schemas.RelacionCliente,
    summary="Realiza un borrado lógico de la Relación"
)
def delete_relacion_endpoint(
    relacion_id: int, 
    servicio: RelacionClienteService = Depends(get_relacion_cliente_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Desactiva (Borrado Lógico) una Relación Cliente-Servicio, 
    estableciendo su estado a "Inactivo" y una fecha de fin (si aplica).
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo Administradores pueden dar de baja relaciones.")
    try:
        return servicio.delete_relacion(relacion_id=relacion_id)
    except NotFoundError as e:
        # Captura NotFoundError si la relación no existe
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))