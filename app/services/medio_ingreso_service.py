# Archivo: app/services/medio_ingreso_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from app.db import models
from app.schemas import medio_ingreso_schema as schemas

class MedioIngresoService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[models.MedioIngreso]:
        return self.db.query(models.MedioIngreso).offset(skip).limit(limit).all()

    def get_by_id(self, id: int) -> models.MedioIngreso:
        medio = self.db.query(models.MedioIngreso).filter(models.MedioIngreso.id_medio_ingreso == id).first()
        if not medio:
            raise HTTPException(status_code=404, detail="Medio de ingreso no encontrado")
        return medio

    def create(self, medio_in: schemas.MedioIngresoCreate) -> models.MedioIngreso:
        # 1. Validar nombre único
        existe = self.db.query(models.MedioIngreso).filter(
            models.MedioIngreso.nombre == medio_in.nombre
        ).first()
        
        if existe:
            raise HTTPException(status_code=409, detail=f"El medio '{medio_in.nombre}' ya existe.")

        # 2. Validar que venga la cuenta (Doble seguridad)
        if not medio_in.id_catalogo:
             raise HTTPException(status_code=400, detail="Debe asignar una Cuenta Contable (Catálogo).")

        # 3. Crear el objeto
        db_obj = models.MedioIngreso(
            nombre=medio_in.nombre,
            tipo=medio_in.tipo,
            requiere_referencia=medio_in.requiere_referencia,
            
            # AQUÍ ESTABA EL ERROR: FALTABA ESTA LÍNEA 👇
            id_catalogo=medio_in.id_catalogo, 
            # ----------------------------------------------
            
            activo=True
        )

        try:
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
            
        except IntegrityError as e:
            self.db.rollback()
            # Esto hace que el error sea "presentable" en el Frontend
            raise HTTPException(status_code=400, detail="Error de integridad: Verifique que la Cuenta Contable exista.")
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error interno al crear medio: {str(e)}")

    def update(self, id: int, medio_in: schemas.MedioIngresoUpdate) -> models.MedioIngreso:
        db_obj = self.get_by_id(id) # Valida 404
        
        # --- 🔒 INICIO VALIDACIÓN DE SEGURIDAD ---
        NOMBRES_PROTEGIDOS = ["efectivo", "caja", "cash"]
        
        # Permitimos actualizar la cuenta de 'Efectivo', pero NO su nombre.
        # Así que verificamos si intenta cambiar el nombre a algo distinto.
        if db_obj.nombre.lower().strip() in NOMBRES_PROTEGIDOS:
             if medio_in.nombre and medio_in.nombre != db_obj.nombre:
                raise HTTPException(
                    status_code=403,
                    detail=f"Acción denegada: No puede cambiar el nombre del registro sistema '{db_obj.nombre}'."
                )
        # --- 🔒 FIN VALIDACIÓN DE SEGURIDAD ---

        # Validar nombre único si está cambiando
        if medio_in.nombre and medio_in.nombre != db_obj.nombre:
             existe = self.db.query(models.MedioIngreso).filter(models.MedioIngreso.nombre == medio_in.nombre).first()
             if existe:
                 raise HTTPException(status_code=409, detail=f"El nombre '{medio_in.nombre}' ya está en uso.")

        # Actualizar campos dinámicamente (Incluye id_catalogo gracias al Schema)
        update_data = medio_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        try:
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
            
        except IntegrityError as e:
            self.db.rollback()
            # Capturamos si el usuario envió un ID de cuenta que no existe
            if "catalogo" in str(e.orig):
                raise HTTPException(status_code=400, detail="La Cuenta Contable seleccionada no existe.")
            
            raise HTTPException(status_code=400, detail="Error de integridad al actualizar.")
    
    def delete(self, id: int):
        # 1. Buscamos el objeto
        db_obj = self.get_by_id(id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Medio de ingreso no encontrado")

        # --- CANDADO DE SEGURIDAD (NUEVO) ---
        # Lista de nombres que JAMÁS se pueden desactivar/borrar
        # Usamos .lower() para evitar problemas de mayúsculas/minúsculas
        NOMBRES_PROTEGIDOS = ["efectivo", "caja", "cash"]
        
        if db_obj.nombre.lower().strip() in NOMBRES_PROTEGIDOS:
            raise HTTPException(
                status_code=403, # Forbidden
                detail=f"ERROR CRÍTICO: El medio '{db_obj.nombre}' es vital para el sistema y no puede ser desactivado."
            )
        # ------------------------------------

        # 2. Verificar uso (Tu lógica histórica)
        uso = self.db.query(models.TransaccionIngreso).filter(models.TransaccionIngreso.id_medio_ingreso == id).first()
        
        if uso:
            # SOFT DELETE (Desactivar si tiene historia, PERO NO ES EFECTIVO)
            db_obj.activo = False
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj 
        else:
            # HARD DELETE (Si es nuevo y sin uso)
            self.db.delete(db_obj)
            self.db.commit()
            return db_obj