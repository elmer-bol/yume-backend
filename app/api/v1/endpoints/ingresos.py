# Archivo: app/api/v1/endpoints/ingresos.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict

# Asumo que esta importación de DB es correcta para tu proyecto
from app.db.database import get_db

# Importamos los Schemas relevantes
# 1. Esquema de respuesta para la Transaccion Ingreso
from app.schemas.transaccion_ingreso_schema import TransaccionIngreso
# 2. Esquema de solicitud que incluye encabezado + detalles (el payload del POST)
from app.schemas.ingreso_request_schema import IngresoTransactionRequest
# NOTA: Eliminamos TransaccionIngresoAnulacion si el PATCH no necesita un cuerpo de solicitud
# from app.schemas.transaccion_ingreso_schema import TransaccionIngresoAnulacion
# 4. Esquema de respuesta para la Transaccion Ingreso Detalle
from app.schemas.transaccion_ingreso_detalle_schema import TransaccionIngresoDetalleBase

# Importamos el Servicio y las Excepciones
from app.services.ingreso_service import IngresoService
from app.core.exceptions import IngresoServiceException, NotFoundException

# Asumo que tienes una función para obtener el ID de usuario del token JWT/sesión
# Reemplazar con tu implementación real de obtención de usuario autenticado
def get_current_user_id() -> int:
    """Dependencia dummy: Retorna un ID de usuario fijo por ahora."""
    # TODO: Implementar lógica real para obtener el ID de usuario autenticado.
    return 1 # ID de ejemplo para fines de demostración/prueba

# ----------------------------------------------------
# DEFINICIÓN DE LA DEPENDENCIA DEL SERVICIO
# ----------------------------------------------------
def get_ingreso_service(db: Session = Depends(get_db)) -> IngresoService:
    """Dependencia que inicializa y provee la instancia de IngresoService."""
    return IngresoService(db)

router = APIRouter(
    prefix="/ingresos",
    tags=["Gestión de Ingresos (Pagos y Cobros)"]
)

# ----------------------------------------------------
# 1. CREATE (POST) - CREACIÓN TRANSACCIONAL
# ----------------------------------------------------
@router.post(
    "/",
    response_model=TransaccionIngreso,
    status_code=status.HTTP_201_CREATED,
    summary="Registra una Transacción de Ingreso (Pago) y aplica a las deudas."
)
def create_ingreso_endpoint(
    ingreso_request: IngresoTransactionRequest, 
    servicio: IngresoService = Depends(get_ingreso_service),
    id_usuario: int = Depends(get_current_user_id)
):
    """
    Registra un Ingreso (pago recibido) de forma transaccional.
    
    Este proceso incluye:
    1. Validar que el monto total coincida con la suma de las aplicaciones.
    2. Crear el encabezado de la TransaccionIngreso.
    3. Crear los detalles de la aplicación del pago.
    4. Actualizar el 'saldo_pendiente' de los ItemFacturable involucrados.
    
    Todo se ejecuta dentro de una transacción de DB.
    """
    try:
        return servicio.create_transaccion_ingreso(ingreso_request, id_usuario)
    except (IngresoServiceException, NotFoundException) as e:
        # Errores de negocio (monto no coincide, item no existe, etc.)
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundException) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        # Error inesperado
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado al crear el ingreso: {str(e)}")


# ----------------------------------------------------
# 2. READ (GET ONE)
# ----------------------------------------------------
@router.get(
    "/{ingreso_id}", 
    response_model=TransaccionIngreso,
    summary="Obtiene una Transacción de Ingreso por su ID."
)
def read_ingreso_endpoint(
    ingreso_id: int,
    servicio: IngresoService = Depends(get_ingreso_service)
):
    """Obtiene el detalle de una transacción de ingreso específica."""
    db_ingreso = servicio.get_transaccion_ingreso_by_id(ingreso_id)
    if db_ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transacción de Ingreso no encontrada")
    return db_ingreso

# ----------------------------------------------------
# 3. READ (GET ALL)
# ----------------------------------------------------
@router.get(
    "/", 
    response_model=List[TransaccionIngreso],
    summary="Obtiene una lista paginada de Transacciones de Ingreso."
)
def read_ingresos_endpoint(
    skip: int = Query(0, description="Número de registros a saltar para paginación"),
    limit: int = Query(100, description="Número máximo de registros a devolver"),
    servicio: IngresoService = Depends(get_ingreso_service)
):
    """Obtiene una lista paginada de todas las transacciones de ingreso."""
    ingresos = servicio.get_transacciones_ingreso(skip=skip, limit=limit)
    return ingresos

# ----------------------------------------------------
# 4. ANULAR (PATCH) - CAMBIO DE ESTADO TRANSACCIONAL
# ----------------------------------------------------
@router.patch(
    "/anular/{ingreso_id}", 
    response_model=TransaccionIngreso,
    summary="Anula una Transacción de Ingreso y revierte los saldos de deuda."
)
def anular_ingreso_endpoint(
    ingreso_id: int,
    # Eliminamos 'anulacion_data' ya que el servicio solo necesita el ID y el usuario.
    servicio: IngresoService = Depends(get_ingreso_service),
    id_usuario: int = Depends(get_current_user_id)
):
    """
    Cambia el estado de una Transacción de Ingreso a 'anulado' y 
    revierte el 'monto_aplicado' al 'saldo_pendiente' de los ItemFacturable 
    asociados, todo de forma transaccional.
    """
    try:
        return servicio.anular_transaccion_ingreso(ingreso_id, id_usuario)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IngresoServiceException as e:
        # Error de negocio (ej: ya está anulado, no se puede anular, etc.)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado al anular el ingreso: {str(e)}")