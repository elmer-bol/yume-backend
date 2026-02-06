# Archivo: app/api/v1/endpoints/categorias.py
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

# Importaciones locales
from app.db.database import get_db
from app.schemas import categoria_schema as schemas
from app.services.categoria_service import CategoriaService 
from app.db import models
# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ADMIN

# ----------------------------------------------------
# DEFINICIÓN DE LA DEPENDENCIA DEL SERVICIO
# ----------------------------------------------------
def get_categoria_service(db: Session = Depends(get_db)) -> CategoriaService:
    """Dependencia que inicializa y provee la instancia de CategoriaService."""
    return CategoriaService(db)

router = APIRouter(
    prefix="/categorias",
    tags=["Catálogo - Cuentas Contables"]
)

# ----------------------------------------------------
# RUTA DE CREACIÓN (POST) - Solo Admin
# ----------------------------------------------------
# CAMBIO: response_model usa CategoriaResponse
@router.post("/", response_model=schemas.CategoriaResponse, status_code=status.HTTP_201_CREATED)
def create_categoria_endpoint(
    categoria: schemas.CategoriaCreate,
    servicio: CategoriaService = Depends(get_categoria_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Crea una nueva Categoría Contable (Con código jerárquico).
    Seguridad: Solo Administradores.
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo administradores pueden crear cuentas contables.")

    try:
        # CAMBIO: Nombre del método en español según el servicio nuevo
        return servicio.crear_categoria(categoria)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------------------------------------------
# RUTAS DE LECTURA (GET) - Todos
# ----------------------------------------------------
@router.get("/", response_model=List[schemas.CategoriaResponse])
def read_categorias_endpoint(
    skip: int = 0,
    limit: int = 100,
    # --- FILTROS NUEVOS ---
    nombre: Optional[str] = Query(None, description="Filtrar por nombre de cuenta"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (ACTIVO, EGRESO...)"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado"),
    es_rubro: Optional[bool] = Query(None, description="True = Solo carpetas, False = Solo cuentas"),
    # ----------------------
    servicio: CategoriaService = Depends(get_categoria_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Obtiene el plan de cuentas completo con filtros opcionales.
    Ej: /categorias?tipo=EGRESO&es_rubro=true
    """
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    # Pasamos los filtros al servicio
    return servicio.get_all_categorias(
        nombre=nombre,
        tipo=tipo,
        activo=activo,
        es_rubro=es_rubro, # <--- Pasamos el nuevo filtro
        skip=skip,
        limit=limit
    )

# ----------------------------------------------------
# RUTA DE ACTUALIZACIÓN (PATCH/PUT) - Solo Admin
# ----------------------------------------------------
# Usamos PATCH porque es actualización parcial en el nuevo schema
@router.patch("/{categoria_id}", response_model=schemas.CategoriaResponse)
def update_categoria_endpoint(
    categoria_id: int,
    categoria_in: schemas.CategoriaUpdate,
    servicio: CategoriaService = Depends(get_categoria_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Actualiza código, nombre o tipo de cuenta. Solo Admin."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para modificar el plan de cuentas.")

    try:
        return servicio.actualizar_categoria(categoria_id, categoria_in)
    except HTTPException as e:
        raise e

# ----------------------------------------------------
# RUTA DE ELIMINACIÓN (DELETE) - Solo Admin
# ----------------------------------------------------
@router.delete("/{categoria_id}")
def delete_categoria_endpoint(
    categoria_id: int,
    servicio: CategoriaService = Depends(get_categoria_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Elimina una cuenta si no tiene movimientos."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para eliminar cuentas.")

    return servicio.eliminar_categoria(categoria_id)