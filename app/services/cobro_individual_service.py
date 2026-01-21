# Archivo: app/services/cobro_individual_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.db import models
from app.schemas import item_facturable_schema as schemas
from app.services.item_facturable_service import ItemFacturableService # <-- Reutiliza la lógica central

class CobroIndividualService:
    """
    Servicio de orquestación para generar cobros únicos, manuales o 'extras'.
    """
    def __init__(self, db: Session):
        self.db = db
        self.item_service = ItemFacturableService(db) # Inicializa el servicio central

    def generar_cobro_instantaneo(self, cobro_data: schemas.ItemFacturableCreate) -> models.ItemFacturable:
        """
        Genera un ItemFacturable único. Aplica la lógica de negocio (R2) 
        a través del ItemFacturableService.
        """
        
        # 1. Validación de existencia de la Unidad (Opcional, pero recomendado)
        # Esto evitaría que se cree una deuda para una unidad inexistente.
        unidad = self.db.query(models.UnidadServicio).filter(models.UnidadServicio.id_unidad == cobro_data.id_unidad).first()
        if not unidad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La Unidad de Servicio no existe.")
            
        # 2. Llamada a la Lógica Central (ItemFacturableService)
        # Aquí se aplica la Regla R2 (No Duplicidad).
        return self.item_service.create_item(cobro_data)
