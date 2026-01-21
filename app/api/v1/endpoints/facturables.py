from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Union

from app.db.database import get_db
from app.db import models
from app.schemas import item_facturable_schema as schemas
from app.services.item_facturable_service import ItemFacturableService

# SEGURIDAD Y AUDITORÍA
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ESCRITURA, ROLES_ADMIN

# ----------------------------------------------------
# DEFINICIÓN DE LA DEPENDENCIA
# ----------------------------------------------------
def get_item_facturable_service(db: Session = Depends(get_db)) -> ItemFacturableService:
    """Dependencia que inicializa y provee la instancia de ItemFacturableService."""
    return ItemFacturableService(db)
    
router = APIRouter(
    prefix="/facturables",
    tags=["Items Facturables (Deuda Generada)"]
)

# ----------------------------------------------------
# ENDPOINTS
# ----------------------------------------------------

# --- 1. CREACIÓN (CON AUDITORÍA) ---

@router.post(
    "/",  
    response_model=schemas.ItemFacturable,  
    status_code=status.HTTP_201_CREATED
)
def create_item_facturable_endpoint(
    item: schemas.ItemFacturableCreate, 
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Genera un nuevo Item Facturable (Deuda).
    Seguridad: Requiere rol de Escritura (Cajero, Admin).
    Auditoría: Registra al usuario creador.
    """
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="No tiene permisos para generar deudas.")
         
    # Pasamos el ID del usuario al servicio para guardarlo en la BD
    return servicio.create_item(item, current_user.id_usuario)

# --- 2. CONSULTAS (LECTURA) ---

@router.get("/", response_model=List[schemas.ItemFacturable])
def read_all_items_facturables_endpoint(
    skip: int = 0,
    limit: int = 100,
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Obtiene una lista paginada de todos los Items Facturables."""
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    items = servicio.get_all_items(skip=skip, limit=limit)
    return items

@router.post("/search", response_model=List[schemas.ItemFacturable])
def search_items_facturables_endpoint(
    filters: schemas.ItemFacturableFilter,
    skip: int = 0,
    limit: int = 100,
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Busqueda avanzada y filtrada."""
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return servicio.get_filtered_items(filters, skip=skip, limit=limit)


@router.get("/unidad/{id_unidad}", response_model=List[schemas.ItemFacturable]) 
def read_items_by_unidad_endpoint(
    id_unidad: int, 
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Obtiene TODAS las deudas de una Unidad específica."""
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return servicio.get_items_by_unidad(id_unidad)

# --- 3. ACTUALIZACIÓN (SOLO ADMIN) ---

@router.patch("/{item_id}", response_model=schemas.ItemFacturable)
def update_item_facturable_endpoint(
    item_id: int, 
    item_in: schemas.ItemFacturableUpdate,
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Actualiza un Item Facturable.
    Seguridad: Solo Administradores.
    Auditoría: Registra quién modificó.
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo administradores pueden modificar deudas.")
         
    return servicio.update_item(item_id, item_in, current_user.id_usuario)


# --- 4. ACCIONES TRANSACCIONALES DE NEGOCIO (SOLO ADMIN) ---

@router.patch("/{item_id}/payment", response_model=schemas.ItemFacturable)
def apply_payment_to_item_endpoint(
    item_id: int,
    monto_pago: float = Body(..., ge=0.01, description="Monto del pago a aplicar."), 
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Aplica un pago manual directo.
    Seguridad: Solo Admin (Cajeros deben usar el módulo de Ingresos).
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Acceso restringido. Use el módulo de Cobranza.")
         
    return servicio.apply_payment(item_id, monto_pago, current_user.id_usuario)

@router.patch("/{item_id}/cancel", response_model=schemas.ItemFacturable)
def cancel_item_facturable_endpoint(
    item_id: int,
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Cancela (anula) un Item Facturable.
    Seguridad: Solo Admin.
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo administradores pueden anular deudas.")
         
    return servicio.cancel_item(item_id, current_user.id_usuario)

# --- 5. TAREA PROGRAMADA / MANTENIMIENTO ---

@router.patch("/overdue-check", response_model=List[schemas.ItemFacturable])
def run_overdue_check_endpoint(
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Simula la ejecución del trabajo CRON."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Proceso reservado para administradores.")
         
    return servicio.check_for_overdue()

# --- 6. GENERACIÓN MASIVA / INTELIGENTE (SOLO ADMIN) ---

@router.post("/generar-periodo", status_code=status.HTTP_201_CREATED)
def generar_cuota_automatica_endpoint(
    datos: schemas.GenerarCuotaRequest, 
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Genera una nueva cuota para una unidad."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Permiso denegado.")
         
    return servicio.generar_cuota_con_cruce(datos, current_user.id_usuario)

@router.post("/generar-masivo", status_code=201)
def generar_cuotas_masivas_endpoint(
    datos: schemas.GenerarMasivoRequest, 
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Genera un bloque de cuotas."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Permiso denegado.")
         
    return servicio.generar_cuotas_masivas(datos, current_user.id_usuario)

@router.post("/generar-global", status_code=200)
def generar_cuotas_globales_endpoint(
    datos: schemas.GenerarGlobalRequest, 
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """El Botón Maestro."""
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Solo SuperAdmin puede ejecutar la generación global.")
         
    return servicio.generar_cuotas_globales(datos, current_user.id_usuario)

# Agrega este endpoint al final de facturables.py

@router.post("/generar-contrato", status_code=200)
def generar_deuda_por_contrato_endpoint(
    datos: schemas.GenerarPorContratoRequest,
    servicio: ItemFacturableService = Depends(get_item_facturable_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Genera un bloque de deudas para UN contrato específico a partir de una fecha.
    Útil para cargar historial (Ej: Generar Ene, Feb, Mar para el Depto 3J).
    """
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="Permiso denegado.")
         
    return servicio.generar_retroactivo_contrato(datos, current_user.id_usuario)