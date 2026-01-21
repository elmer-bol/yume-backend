# Archivo: app/schemas/ingreso_request_schema.py
from pydantic import BaseModel, Field
from typing import List
# Necesitamos importar TransaccionIngresoBase desde su ubicación relativa
# Asumiendo que está en el mismo nivel, usamos un import relativo.
from ..schemas.transaccion_ingreso_schema import TransaccionIngresoBase

# 1. Esquema de Detalle para la Solicitud (Solo los campos necesarios para aplicar el pago)
class IngresoDetalleApplication(BaseModel):
    """
    Representa la aplicación de una parte del pago a un ItemFacturable específico.
    Se usa en el payload de creación de la transacción.
    """
    id_item: int = Field(..., description="ID del Item Facturable (la deuda) a la que se aplica el pago.")
    monto_aplicado: float = Field(..., gt=0, description="Monto exacto que se aplica a este ItemFacturable.")

# 2. Esquema Completo de Creación de Ingreso
class IngresoTransactionRequest(TransaccionIngresoBase):
    """
    Esquema principal para el endpoint POST /ingresos/. 
    Combina el encabezado de la transacción (heredado de TransaccionIngresoBase) 
    con la lista de aplicaciones (detalles de pago).
    """
    detalles_aplicacion: List[IngresoDetalleApplication] = Field(
        ..., 
        min_length=1, 
        description="Lista de aplicaciones del pago a uno o más Items Facturables."
    )