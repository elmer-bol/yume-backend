# Archivo: app/services/medio_ingreso_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from typing import List

from app.db import models
from app.schemas import medio_ingreso_schema as schemas

class MedioIngresoService:
    def __init__(self, db: Session):
        self.db = db

    # --- Helper Privado ---
    def _validar_cuenta_activo(self, id_catalogo: int):
        """Asegura que la cuenta seleccionada sea un ACTIVO (Caja/Banco)."""
        cuenta = self.db.query(models.Categoria).filter(models.Categoria.id_catalogo == id_catalogo).first()
        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta contable no encontrada")
        
        # Validamos por tipo 'ACTIVO' o por código que empiece con '1'
        es_activo = cuenta.tipo == 'ACTIVO' or str(cuenta.codigo).startswith('1')
        
        if not es_activo:
            raise HTTPException(
                status_code=400, 
                detail=f"La cuenta '{cuenta.nombre_cuenta}' NO es un Activo. Las billeteras solo pueden enlazarse a cuentas del Grupo 1 (Activos)."
            )

    def get_all(self, skip: int = 0, limit: int = 100):
        medios = self.db.query(models.MedioIngreso).offset(skip).limit(limit).all()
        
        # Mapeo manual para incluir datos de la cuenta contable
        resultados = []
        for m in medios:
            # Convertimos al nuevo schema Response
            resp = schemas.MedioIngresoResponse.model_validate(m)
            
            # Inyectamos datos visuales si existen
            if m.cuenta_contable:
                resp.nombre_cuenta = m.cuenta_contable.nombre_cuenta
                resp.codigo_cuenta = m.cuenta_contable.codigo
            
            resultados.append(resp)
            
        return resultados

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

        # 2. Validar Cuenta Contable (ACTIVO)
        self._validar_cuenta_activo(medio_in.id_catalogo)

        # 3. Crear el objeto
        db_obj = models.MedioIngreso(
            nombre=medio_in.nombre,
            tipo=medio_in.tipo,
            requiere_referencia=medio_in.requiere_referencia,
            id_catalogo=medio_in.id_catalogo,     # Enlace Contable
            limite_maximo=medio_in.limite_maximo, # Regla de Negocio
            activo=True
        )

        try:
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
            
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Error de integridad: Verifique datos.")
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

    def update(self, id: int, medio_in: schemas.MedioIngresoUpdate) -> models.MedioIngreso:
        db_obj = self.get_by_id(id) # Valida 404
        
        # --- 🔒 SEGURIDAD: PROTECCIÓN DE NOMBRES CRÍTICOS ---
        NOMBRES_PROTEGIDOS = ["efectivo", "caja", "cash"]
        if db_obj.nombre.lower().strip() in NOMBRES_PROTEGIDOS:
             # Si intenta cambiar el nombre a algo distinto
             if medio_in.nombre and medio_in.nombre != db_obj.nombre:
                raise HTTPException(
                    status_code=403,
                    detail=f"Acción denegada: No puede renombrar el registro de sistema '{db_obj.nombre}'."
                )

        # Validar nombre único si cambia
        if medio_in.nombre and medio_in.nombre != db_obj.nombre:
             existe = self.db.query(models.MedioIngreso).filter(models.MedioIngreso.nombre == medio_in.nombre).first()
             if existe:
                 raise HTTPException(status_code=409, detail=f"El nombre '{medio_in.nombre}' ya está en uso.")

        # Validar cuenta contable si cambia
        if medio_in.id_catalogo:
            self._validar_cuenta_activo(medio_in.id_catalogo)

        # Actualizar campos dinámicamente
        update_data = medio_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        try:
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
            
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Error de integridad al actualizar.")
    
    def delete(self, id: int):
        db_obj = self.get_by_id(id)
        
        # --- 🔒 SEGURIDAD ---
        NOMBRES_PROTEGIDOS = ["efectivo", "caja", "cash"]
        if db_obj.nombre.lower().strip() in NOMBRES_PROTEGIDOS:
            raise HTTPException(
                status_code=403,
                detail=f"ERROR CRÍTICO: El medio '{db_obj.nombre}' es vital y no puede eliminarse."
            )

        # Verificar uso histórico
        uso = self.db.query(models.TransaccionIngreso).filter(models.TransaccionIngreso.id_medio_ingreso == id).first()
        
        if uso:
            # SOFT DELETE
            db_obj.activo = False
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj 
        else:
            # HARD DELETE
            self.db.delete(db_obj)
            self.db.commit()
            return db_obj