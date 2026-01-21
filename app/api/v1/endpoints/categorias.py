from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

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
@router.post("/", response_model=schemas.Categoria, status_code=status.HTTP_201_CREATED)
def create_categoria_endpoint(
    categoria: schemas.CategoriaCreate,
    servicio: CategoriaService = Depends(get_categoria_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Crea una nueva Categoría Contable.
    Seguridad: Solo Administradores (SuperAdmin, AdminEdif).
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo administradores pueden crear cuentas contables.")

    try:
        return servicio.create_categoria(categoria)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=str(e)
        )

# ----------------------------------------------------
# RUTAS DE LECTURA (GET) - Todos
# ----------------------------------------------------
@router.get("/", response_model=List[schemas.Categoria])
def read_categorias_endpoint(
    filters: schemas.CategoriaFilter = Depends(),
    skip: int = 0,
    limit: int = 100,
    servicio: CategoriaService = Depends(get_categoria_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Obtiene la lista de categorías. Acceso: Todos los roles."""
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    return servicio.get_all_categorias(filters=filters, skip=skip, limit=limit)

def get_categoria_or_404(
    categoria_id: int,
    servicio: CategoriaService = Depends(get_categoria_service)
) -> models.Categoria:
    """Helper para buscar categoría o lanzar error."""
    db_categoria = servicio.get_categoria_by_id(categoria_id=categoria_id)

    if db_categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Categoría con ID {categoria_id} no encontrada"
        )
    return db_categoria

@router.get("/{categoria_id}", response_model=schemas.Categoria)
def read_categoria_by_id_endpoint(
    db_categoria: models.Categoria = Depends(get_categoria_or_404),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Obtiene una Categoría por ID."""
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return db_categoria

# ----------------------------------------------------
# RUTA DE ACTUALIZACIÓN (PUT) - Solo Admin
# ----------------------------------------------------
@router.put("/{categoria_id}", response_model=schemas.Categoria)
def update_categoria_endpoint(
    categoria_in: schemas.CategoriaUpdate,
    db_categoria: models.Categoria = Depends(get_categoria_or_404),
    servicio: CategoriaService = Depends(get_categoria_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Actualiza una Categoría. Solo Admin."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para modificar el plan de cuentas.")

    try:
        updated_categoria = servicio.update_categoria(db_categoria, categoria_in)
        return updated_categoria
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=str(e)
        )

# ----------------------------------------------------
# RUTA DE ELIMINACIÓN LÓGICA (DELETE) - Solo Admin
# ----------------------------------------------------
@router.delete("/{categoria_id}", response_model=schemas.Categoria)
def delete_categoria_endpoint(
    db_categoria: models.Categoria = Depends(get_categoria_or_404),
    servicio: CategoriaService = Depends(get_categoria_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Desactiva una Categoría. Solo Admin."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para eliminar cuentas.")

    return servicio.deactivate_categoria(db_categoria)