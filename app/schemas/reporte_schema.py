from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

# 1. BLOQUES PEQUEÑOS (Los ladrillos)

class ItemDeuda(BaseModel):
    """Representa una fila en la tabla de 'Lo que debo'"""
    periodo: str
    concepto: str
    monto_base: float
    saldo_pendiente: float
    fecha_vencimiento: date
    estado: str
    # Opcional: días de retraso si quisieras calcularlo

class ItemPago(BaseModel):
    """Representa una fila en la tabla de 'Lo que pagué'"""
    fecha: datetime
    monto_total: float
    descripcion: str
    num_documento: Optional[str] = None
    medio_pago: str # Ej: "Transferencia", "QR"

# 2. EL RESUMEN (Los números grandes)

class ResumenFinanciero(BaseModel):
    total_deuda_vencida: float
    total_deuda_pendiente: float  # Suma de todo lo que debe
    saldo_a_favor_disponible: float # Lo que tiene en Billetera
    estado_general: str # "Al día", "Moroso", "Solvente"

# 3. EL REPORTE FINAL (El edificio completo)

class EstadoCuentaResponse(BaseModel):
    fecha_reporte: datetime
    id_persona: int
    nombre_persona: str
    
    resumen: ResumenFinanciero
    
    # Las listas de detalles
    billeteras: List[dict] # Por si tiene saldo en varias unidades
    deudas_pendientes: List[ItemDeuda]
    ultimos_pagos: List[ItemPago]

# 4. REPORTE GERENCIAL (TABLA DE MOROSIDAD)

class DetalleDeudaMoroso(BaseModel):
    periodo: str
    concepto: str  # <--- NUEVO CAMPO AGREGADO
    monto_pendiente: float
    dias_atraso: int

class MorosoResponse(BaseModel):
    """Fila para la tabla del Dashboard de Administrador"""
    id_unidad: int
    identificador_unico: str
    nombre_inquilino: str
    total_deuda: float
    cantidad_meses: int
    detalles: List[DetalleDeudaMoroso] = []

    class Config:
        from_attributes = True