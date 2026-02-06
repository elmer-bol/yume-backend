# Archivo: app/schemas/caja_schema.py
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional

# --- MODELO 1: EL BALANCE (FOTO DEL MOMENTO) ---
class BalanceCaja(BaseModel):
    total_ingresos_efectivo: float
    total_gastos_realizados: float
    total_depositos_bancarios: float
    
    saldo_actual_en_caja: float
    fecha_corte: datetime

    class Config:
        from_attributes = True

# --- MODELO 2: EL MOVIMIENTO (FILA DEL REPORTE) ---
class MovimientoCaja(BaseModel):
    fecha: datetime
    tipo: str  # 'INGRESO', 'GASTO', 'DEPOSITO'
    descripcion: str
    monto_entrada: float = 0.0
    monto_salida: float = 0.0
    
    referencia_id: int # ID de la transacción original
    usuario_responsable: str

    class Config:
        from_attributes = True

# --- MODELO 3: EL LIBRO DIARIO COMPLETO ---
class ReporteLibroCaja(BaseModel):
    saldo_actual: float
    movimientos: List[MovimientoCaja]

# --- MODELO 4: TRANSFERENCIA DE EFECTIVO CAJA CHICA ---
class TransferenciaCreate(BaseModel):
    monto: float
    id_medio_origen: int  # Ej: ID del Banco (Donde sale la plata)
    id_medio_destino: int # Ej: ID de la Caja Chica (Donde entra)
    fecha: date
    descripcion: Optional[str] = "Transferencia de fondos"