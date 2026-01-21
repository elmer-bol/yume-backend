from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date

# --------------------------------------------------------
# 1. Esquemas "Ligeros" para anidar (Para que el Frontend vea nombres)
# --------------------------------------------------------
class PersonaSimple(BaseModel):
    nombres: str
    apellidos: str
    ci_nit: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class UnidadSimple(BaseModel):
    identificador_unico: str
    tipo_unidad: str
    
    model_config = ConfigDict(from_attributes=True)

# --------------------------------------------------------
# 2. Esquemas Base y FILTRO (¡Esto es lo que faltaba!)
# --------------------------------------------------------
class RelacionClienteBase(BaseModel):
    id_persona: int
    id_unidad: int
    fecha_inicio: date
    tipo_relacion: str
    fecha_fin: Optional[date] = None
    monto_mensual: Optional[float] = 0.0
    dia_pago: int = 5
    estado: str = "Activo"
    saldo_favor: float = 0.0

# 👇 ESTA ES LA CLASE QUE RECLAMA TU ERROR 👇
class RelacionClienteFilter(BaseModel):
    id_persona: Optional[int] = None
    id_unidad: Optional[int] = None
    estado: Optional[str] = None
    tipo_relacion: Optional[str] = None  # <--- ESTO FALTABA PARA QUE NO EXPLOTE

# --------------------------------------------------------
# 3. Create & Update
# --------------------------------------------------------
class RelacionClienteCreate(RelacionClienteBase):
    pass

class RelacionClienteUpdate(BaseModel):
    id_unidad: Optional[int] = None
    tipo_relacion: Optional[str] = None 
    fecha_inicio: Optional[date] = None

    fecha_fin: Optional[date] = None
    monto_mensual: Optional[float] = None
    dia_pago: Optional[int] = None
    estado: Optional[str] = None

# --------------------------------------------------------
# 4. Response (LECTURA)
# --------------------------------------------------------
class RelacionCliente(RelacionClienteBase):
    id_relacion: int
    
    # Aquí es donde ocurre la "hidratación" de datos
    persona: Optional[PersonaSimple] = None
    unidad: Optional[UnidadSimple] = None

    model_config = ConfigDict(from_attributes=True)