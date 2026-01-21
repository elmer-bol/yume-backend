from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date, datetime

# --- 1. LO QUE SE MUESTRA EN LA LISTA DE CHECKBOXES (PENDIENTES) ---
class TransaccionPendiente(BaseModel):
    id_transaccion: int
    fecha: date
    monto_total: float
    descripcion: Optional[str] = None
    nombre_pagador: str = "Desconocido" 

    class Config:
        from_attributes = True

# --- 2. INPUT: LO QUE ENVÍA EL ADMIN PARA CERRAR CAJA ---
class DepositoCreate(BaseModel):
    fecha: date
    monto: float = Field(..., gt=0)
    num_referencia: str = Field(..., min_length=3, description="Número de voucher o comprobante bancario")
    banco: str = Field(..., min_length=2, description="Nombre del banco destino")
    cuenta_destino: str = Field(..., min_length=2, description="Número de cuenta del edificio")
    
    # SEGURIDAD: Eliminado. Lo tomamos del Token.
    # id_administrador: int
    
    # LA CLAVE DEL BLINDAJE: Lista de IDs de transacciones a "limpiar"
    transacciones_ids: List[int] = Field(..., min_length=1)

    @field_validator('monto')
    def monto_positivo(cls, v):
        if v <= 0:
            raise ValueError('El monto debe ser positivo')
        return v

# --- 3. OUTPUT: RESPUESTA DEL DEPÓSITO CREADO ---
class DepositoResponse(BaseModel):
    id_deposito: int
    fecha: date
    monto: float
    num_referencia: str
    banco: str
    cuenta_destino: str
    estado: str
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True