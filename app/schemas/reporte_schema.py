from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

# ==========================================
# 1. REPORTES EXISTENTES (OPERATIVOS)
# ==========================================

# 1.1. BLOQUES PEQUEÑOS (Los ladrillos)
class ItemDeuda(BaseModel):
    """Representa una fila en la tabla de 'Lo que debo'"""
    periodo: str
    concepto: str
    monto_base: float
    saldo_pendiente: float
    fecha_vencimiento: date
    estado: str

    id_unidad: Optional[int] = None
    nombre_unidad: Optional[str] = None

class ItemPago(BaseModel):
    """Representa una fila en la tabla de 'Lo que pagué'"""
    fecha: datetime
    monto_total: float
    descripcion: str
    num_documento: Optional[str] = None
    medio_pago: str 

# 1.2. EL RESUMEN (Los números grandes)
class ResumenFinanciero(BaseModel):
    total_deuda_vencida: float
    total_deuda_pendiente: float  
    saldo_a_favor_disponible: float 
    estado_general: str 

# 1.3. ESTADO DE CUENTA INDIVIDUAL
class EstadoCuentaResponse(BaseModel):
    fecha_reporte: datetime
    id_persona: int
    nombre_persona: str
    
    resumen: ResumenFinanciero
    
    billeteras: List[dict] 
    deudas_pendientes: List[ItemDeuda]
    ultimos_pagos: List[ItemPago]

# 1.4. REPORTE DE MOROSIDAD
class DetalleDeudaMoroso(BaseModel):
    periodo: str
    concepto: str  
    monto_pendiente: float
    dias_atraso: int

class MorosoResponse(BaseModel):
    id_unidad: int
    identificador_unico: str
    nombre_inquilino: str
    total_deuda: float
    cantidad_meses: int
    detalles: List[DetalleDeudaMoroso] = []

    class Config:
        from_attributes = True

# 1.5. CARTERA GLOBAL
class CarteraGlobalResponse(BaseModel):
    id_unidad: int
    identificador_unico: str
    nombre_inquilino: str
    deuda_vencida: float   
    deuda_futura: float    
    total_general: float   
    cantidad_items: int    

    class Config:
        from_attributes = True

# ==========================================
# 2. NUEVO: REPORTE CONTABLE JERÁRQUICO
# ==========================================

class NodoReporte(BaseModel):
    """
    Un nodo del árbol contable.
    Ej: "5.1 Servicios Básicos" (que contiene adentro a Luz y Agua)
    """
    id_catalogo: Optional[int] = None
    codigo: str
    nombre: str
    monto: float      # La suma total (propio + hijos)
    nivel: int        # 1, 2, 3...
    es_rubro: bool    # Si es carpeta o cuenta final
    hijos: List['NodoReporte'] = [] 

class EstadoResultadosResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    
    # Los dos grandes árboles
    ingresos: NodoReporte # Raíz del Grupo 4
    egresos: NodoReporte  # Raíz del Grupo 5
    
    # Totales rápidos
    total_ingresos: float
    total_egresos: float
    resultado_neto: float # Superávit o Déficit

    # --- NUEVOS CAMPOS ---
    saldo_anterior: float = 0.0  # Lo que sobró antes de fecha_inicio
    saldo_final_acumulado: float = 0.0 # saldo_anterior + resultado_neto

    class Config:
        from_attributes = True
# ... (Mantén tus clases anteriores: EstadoCuentaResponse, NodoReporte, etc.) ...

# -----------------------------------------------------------------------------
# NUEVO: MODELOS PARA EL DASHBOARD (HOME)
# -----------------------------------------------------------------------------

class SaldoBilletera(BaseModel):
    nombre: str
    monto: float
    tipo: str # 'caja' o 'banco'

class DashboardResponse(BaseModel):
    total_disponible: float      # Suma de todas las billeteras (Activos)
    total_por_cobrar: float      # Deuda vencida + futura de todos
    cantidad_morosos: int        # Cuánta gente debe plata vencida
    
    billeteras: List[SaldoBilletera]  # Desglose de dónde está la plata
    top_morosos: List[MorosoResponse] # Reutilizamos la clase de morosos existente

# ... (al final del archivo)

class DetalleMovimientoResponse(BaseModel):
    fecha: date
    descripcion: str                # Ej: "Pago de Expensas Enero" o "Compra de Escobas"
    beneficiario_o_pagador: str     # Ej: "Juan Perez" (Inquilino) o "Ferreteria El Clavo" (Proveedor)
    nro_documento: Optional[str] = None
    monto: float
    tipo: str                       # 'INGRESO' o 'EGRESO'

# ==========================================
# NUEVO: REPORTE LIBRO DIARIO (CAJA)
# ==========================================

class MovimientoCaja(BaseModel):
    fecha: date | datetime
    descripcion: str
    numero_doc: Optional[str] = None
    ingreso: float
    egreso: float
    saldo_acumulado: float 
    origen: Optional[str] = None

class ReporteCajaResponse(BaseModel):
    id_medio: int
    nombre_medio: str
    fecha_inicio: date
    fecha_fin: date
    saldo_inicial: float 
    movimientos: List[MovimientoCaja]
    saldo_final: float