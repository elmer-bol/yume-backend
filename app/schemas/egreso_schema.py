# Archivo: app/schemas/egreso_schema.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date, datetime
from typing import Optional

# ======================================================================
# 1. MINI-ESQUEMAS (Mapeados exactamente a tus modelos)
# ======================================================================

class TipoEgresoInfo(BaseModel):
    nombre: str
    model_config = ConfigDict(from_attributes=True)

class MedioPagoInfo(BaseModel):
    nombre: str
    model_config = ConfigDict(from_attributes=True)

class CuentaInfo(BaseModel):
    nombre_cuenta: str  
    codigo: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# ======================================================================
# 2. INPUT: REGISTRAR GASTO
# ======================================================================
class EgresoCreate(BaseModel):
    id_tipo_egreso: int = Field(..., description="Carpeta organizadora (Mantenimiento, Servicios, etc.)")
    
    # CUENTA CONTABLE (EN QUÉ GASTÉ - DEBE)
    id_catalogo: int = Field(..., description="Cuenta contable del gasto (Debe ser tipo EGRESO)")
    
    # ORIGEN DE FONDOS (CON QUÉ PAGUÉ - HABER)
    id_medio_pago: int = Field(..., description="Billetera de origen (Caja o Banco)")
    
    monto: float = Field(..., gt=0, description="Monto gastado")
    fecha: date
    beneficiario: str = Field(..., min_length=3, description="A quién se le pagó")
    num_comprobante: Optional[str] = Field(None, description="Número de factura o recibo")
    descripcion: Optional[str] = None

    @field_validator('monto')
    def validar_monto(cls, v):
        if v <= 0:
            raise ValueError("El monto del gasto debe ser mayor a 0")
        return v

# ======================================================================
# 3. OUTPUT: RESPUESTA AL FRONTEND
# ======================================================================
class EgresoResponse(BaseModel):
    id_egreso: int
    monto: float
    fecha: date
    beneficiario: str
    num_comprobante: Optional[str] = None
    descripcion: Optional[str] = None
    estado: str
    fecha_creacion: datetime

    # Objetos anidados (Coinciden con las relaciones en models.py)
    catalogo: Optional[CuentaInfo] = None
    tipo_egreso: Optional[TipoEgresoInfo] = None
    medio_pago: Optional[MedioPagoInfo] = None 

    # Configuración moderna de Pydantic v2
    model_config = ConfigDict(from_attributes=True)