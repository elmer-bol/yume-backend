from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.schemas import concepto_deuda_schema as schemas
from app.services.concepto_deuda_service import ConceptoDeudaService

# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ADMIN

def get_concepto_deuda_service(db: Session = Depends(get_db)) -> ConceptoDeudaService:
    return ConceptoDeudaService(db)
    
router = APIRouter(
    prefix="/conceptos",
    tags=["Conceptos de Deuda (Catálogo)"]
)

# 1. CREAR (Solo Admin)
@router.post("/", response_model=schemas.ConceptoDeuda, status_code=status.HTTP_201_CREATED)
def create_concepto_endpoint(
    concepto: schemas.ConceptoDeudaCreate, 
    servicio: ConceptoDeudaService = Depends(get_concepto_deuda_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo administradores pueden crear conceptos de deuda.")
         
    return servicio.create_concepto(concepto)

# 2. LISTAR (Todos)
@router.get("/", response_model=List[schemas.ConceptoDeuda])
def read_all_conceptos_endpoint(
    skip: int = 0, limit: int = 100, 
    servicio: ConceptoDeudaService = Depends(get_concepto_deuda_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return servicio.get_all_conceptos(skip=skip, limit=limit)

# 3. LEER UNO (Todos)
@router.get("/{concepto_id}", response_model=schemas.ConceptoDeuda)
def read_concepto_by_id_endpoint(
    concepto_id: int, 
    servicio: ConceptoDeudaService = Depends(get_concepto_deuda_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    db_concepto = servicio.get_concepto_by_id(concepto_id=concepto_id)
    if db_concepto is None:
        raise HTTPException(status_code=404, detail="Concepto de Deuda no encontrado")
    return db_concepto

# 4. ACTUALIZAR (Solo Admin)
@router.patch("/{concepto_id}", response_model=schemas.ConceptoDeuda)
def update_concepto_endpoint(
    concepto_id: int,
    concepto_in: schemas.ConceptoDeudaUpdate,
    servicio: ConceptoDeudaService = Depends(get_concepto_deuda_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Actualiza un concepto (Nombre, Descripción, Monto Sugerido).
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para modificar conceptos.")
         
    return servicio.update_concepto(concepto_id, concepto_in)

# 5. ELIMINAR (Solo Admin)
@router.delete("/{concepto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concepto_endpoint(
    concepto_id: int,
    servicio: ConceptoDeudaService = Depends(get_concepto_deuda_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Elimina un concepto SI Y SOLO SI no tiene historial de deudas.
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="No tiene permisos para eliminar conceptos.")
         
    servicio.delete_concepto(concepto_id)