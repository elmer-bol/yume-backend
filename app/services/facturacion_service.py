# Archivo: app/services/facturacion_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.db import models
from app.schemas import item_facturable_schema as schemas
from app.services.item_facturable_service import ItemFacturableService # Para crear la deuda con reglas (R2)
from datetime import date, timedelta
from typing import Dict, Any

class FacturacionService:
    """
    Servicio de orquestación para la generación masiva de cobros mensuales.
    """
    def __init__(self, db: Session):
        self.db = db
        self.item_service = ItemFacturableService(db)

    def generar_cobros_mensuales(self, fecha_facturacion: date, id_concepto_mensual: int) -> Dict[str, Any]:
        """
        Genera ItemFacturable (deudas) para todas las RelacionesCliente activas.
        Aplica la Regla R1: Solo relaciones activas.
        """
        
        # 1. Preparación y Búsqueda de Concepto (R3 implícita)
        # Se requiere el Concepto para obtener el monto y nombre.
        concepto_deuda = self.db.query(models.ConceptoDeuda).filter(
            models.ConceptoDeuda.id_concepto == id_concepto_mensual
        ).first()
        
        if not concepto_deuda:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concepto de Deuda no encontrado.")
            
        monto_a_cobrar = concepto_deuda.monto_base # Asumimos que el Concepto tiene un monto_base
        periodo_str = fecha_facturacion.strftime("%Y-%m") # Ejemplo: '2025-11'
        
        # CÁLCULO CLAVE: DETERMINAR FECHA DE VENCIMIENTO
        # Regla de Negocio Asumida: Vencimiento 15 días después de la fecha de facturación.
        fecha_vencimiento = fecha_facturacion + timedelta(days=15)

        # 2. REGLA R1: Obtener Relaciones Clientes Activas
        # Filtra las relaciones que están ACTIVAS para la fecha de facturación.
        relaciones_activas = self.db.query(models.RelacionCliente).filter(
            models.RelacionCliente.estado == 'Activo',
            models.RelacionCliente.fecha_inicio <= fecha_facturacion,
            # La relación está vigente si fecha_fin es NULL O si fecha_fin es posterior a la fecha de facturación
            (models.RelacionCliente.fecha_fin == None) | (models.RelacionCliente.fecha_fin >= fecha_facturacion)
        ).all()
        
        cobros_generados = 0
        cobros_duplicados = 0
        
        # 3. Iterar y Orquestar la Creación de Deudas
        for relacion in relaciones_activas:
            # Crear el objeto de datos para la deuda (ItemFacturableCreate)
            item_data = schemas.ItemFacturableCreate(
                id_unidad=relacion.id_unidad,
                id_persona=relacion.id_persona, 
                id_concepto=id_concepto_mensual,
                monto_base=monto_a_cobrar,
                periodo=periodo_str
                # Nota: Deberás añadir aquí la lógica para calcular fecha_vencimiento
            )
            
            try:
                # Llama al servicio central (ItemFacturableService) que aplica la Regla R2 (No Duplicidad)
                self.item_service.create_item_con_reglas(item_data)
                cobros_generados += 1
            except HTTPException as e:
                # Ignoramos la duplicidad, ya que es esperado en un proceso masivo
                if e.status_code == status.HTTP_400_BAD_REQUEST and "duplicidad" in e.detail:
                    cobros_duplicados += 1
                    continue
                # Lanzar otros errores inesperados
                raise e
                
        return {
            "estado": "Finalizado", 
            "periodo": periodo_str, 
            "cobros_generados": cobros_generados, 
            "cobros_duplicados_omitidos": cobros_duplicados,
            "total_relaciones_evaluadas": len(relaciones_activas)
        }
