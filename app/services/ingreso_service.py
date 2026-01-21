# Archivo: app/services/ingreso_service.py
from sqlalchemy.orm import Session
from sqlalchemy import text 
from typing import List, Optional
from datetime import datetime

# Importamos las excepciones personalizadas
from app.core.exceptions import IngresoServiceException, NotFoundException

# Importamos los Schemas de Pydantic
from app.schemas.transaccion_ingreso_schema import (
    TransaccionIngreso, TransaccionIngresoBase
)
from app.schemas.transaccion_ingreso_detalle_schema import TransaccionIngresoDetalleBase
from app.schemas.ingreso_request_schema import IngresoTransactionRequest

# FUENTE CENTRAL CORRECTA: Importamos los modelos ORM desde app.db
from app.db import models 

# Definimos los alias DE MODELO para mantener la claridad en la lógica del servicio
TransaccionIngresoModel = models.TransaccionIngreso
TransaccionIngresoDetalleModel = models.TransaccionIngresoDetalle
ItemFacturableModel = models.ItemFacturable
# CORRECCIÓN: Usamos 'MedioIngreso' que es el nombre correcto en models.py
CatalogoMedioIngresoModel = models.MedioIngreso 


class IngresoService:
    """
    Servicio de lógica de negocio para gestionar Transacciones de Ingreso (Pagos).
    """

    def __init__(self, db: Session):
        """Inicializa el servicio con una sesión de base de datos."""
        self.db = db
    
    # =========================================================================
    # LÓGICA DE CREACIÓN DE INGRESO (TRANSACCIONAL)
    # =========================================================================

    def create_transaccion_ingreso(
        self, 
        ingreso_data: IngresoTransactionRequest,
        id_usuario_autenticado: int
    ) -> TransaccionIngresoModel:
        """
        Crea una Transacción de Ingreso completa (encabezado, detalles) 
        y actualiza los saldos de ItemFacturable, todo en una sola transacción.
        """
        try:
            # 1. Validación de Montos (Ingreso Total vs. Suma de Aplicaciones)
            total_detalles = sum(d.monto_aplicado for d in ingreso_data.detalles_aplicacion)
            
            # Usamos una tolerancia pequeña para evitar problemas de punto flotante
            if abs(ingreso_data.monto_total - total_detalles) > 0.01:
                raise IngresoServiceException(
                    f"El monto total ({ingreso_data.monto_total:.2f}) no coincide "
                    f"con la suma de los detalles ({total_detalles:.2f})."
                )

            # 2. Creación del Encabezado (TransaccionIngreso)
            ingreso_header_dict = ingreso_data.model_dump(exclude={'detalles_aplicacion'})
            
            db_ingreso = TransaccionIngresoModel(
                **ingreso_header_dict,
                fecha_creacion=datetime.now(),
                id_usuario_creador=id_usuario_autenticado,
                estado='registrado' # Estado inicial
            )
            self.db.add(db_ingreso)
            self.db.flush() # Forzar la inserción para obtener el ID de ingreso

            # 3. Procesamiento y Creación de Detalles (TransaccionIngresoDetalle)
            for detalle_req in ingreso_data.detalles_aplicacion:
                
                # A. Buscar y Validar ItemFacturable
                db_item = self.db.query(ItemFacturableModel).get(detalle_req.id_item)
                if not db_item:
                    raise NotFoundException(f"ItemFacturable con ID {detalle_req.id_item} no encontrado.")

                # Validación de saldo pendiente
                if detalle_req.monto_aplicado > db_item.saldo_pendiente + 0.01:
                    raise IngresoServiceException(
                        f"Monto aplicado ({detalle_req.monto_aplicado:.2f}) excede el saldo pendiente "
                        f"({db_item.saldo_pendiente:.2f}) para ItemFacturable ID {detalle_req.id_item}."
                    )
                
                # B. Crear Detalle
                db_detalle = TransaccionIngresoDetalleModel(
                    id_transaccion_ingreso=db_ingreso.id,
                    id_item_facturable=detalle_req.id_item,
                    monto_aplicado=detalle_req.monto_aplicado,
                )
                self.db.add(db_detalle)
                
                # C. Actualizar Saldo Pendiente del ItemFacturable
                nuevo_saldo = db_item.saldo_pendiente - detalle_req.monto_aplicado
                db_item.saldo_pendiente = round(nuevo_saldo, 2)
                
                # Actualizar estado si el saldo llega a cero
                if db_item.saldo_pendiente <= 0.01:
                    db_item.estado = 'pagado'
                else:
                    db_item.estado = 'pago_parcial' 
                
                self.db.add(db_item) # Marcar para actualización
            
            # 4. Confirmación de la Transacción (COMMIT)
            db_ingreso.estado = 'aplicado' # Cambiar el estado del ingreso a aplicado
            self.db.commit()
            self.db.refresh(db_ingreso)
            return db_ingreso

        except (IngresoServiceException, NotFoundException, Exception) as e:
            # 5. Rollback en caso de cualquier error
            self.db.rollback()
            if isinstance(e, (IngresoServiceException, NotFoundException)):
                raise e
            raise IngresoServiceException(f"Error fatal durante la transacción de ingreso: {str(e)}")


    # =========================================================================
    # LÓGICA DE ANULACIÓN DE INGRESO (TRANSACCIONAL)
    # =========================================================================

    def anular_transaccion_ingreso(self, transaccion_id: int, id_usuario_modificador: int) -> TransaccionIngresoModel:
        """
        Anula una Transacción de Ingreso y revierte los saldos de los ItemFacturable afectados.
        """
        try:
            db_ingreso = self.db.query(TransaccionIngresoModel).get(transaccion_id)
            if not db_ingreso:
                raise NotFoundException(f"Transacción de Ingreso con ID {transaccion_id} no encontrada.")

            if db_ingreso.estado == 'anulado':
                raise IngresoServiceException("La transacción ya se encuentra anulada.")

            # 1. Revertir saldos de ItemFacturable
            detalles = self.db.query(TransaccionIngresoDetalleModel).filter(
                TransaccionIngresoDetalleModel.id_transaccion_ingreso == transaccion_id
            ).all()

            for detalle in detalles:
                db_item = self.db.query(ItemFacturableModel).get(detalle.id_item_facturable)
                
                if not db_item:
                    print(f"Advertencia: ItemFacturable ID {detalle.id_item_facturable} no encontrado durante anulación.")
                    continue
                
                # Sumar el monto aplicado de nuevo al saldo pendiente
                db_item.saldo_pendiente = round(db_item.saldo_pendiente + detalle.monto_aplicado, 2)
                
                # Si el saldo pendiente es mayor a cero, el estado vuelve a 'pendiente'
                if db_item.saldo_pendiente > 0:
                    db_item.estado = 'pendiente' 
                
                self.db.add(db_item)

            # 2. Actualizar el estado de la Transacción de Ingreso
            db_ingreso.estado = 'anulado'
            # NOTA: En el modelo original falta el campo fecha_anulacion.
            # Lo omitiremos aquí para evitar un error, pero se recomienda agregarlo al ORM.
            db_ingreso.fecha_anulacion = datetime.now() 
            db_ingreso.id_usuario_modificador = id_usuario_modificador
            self.db.add(db_ingreso)

            # 3. Confirmación de la Transacción (COMMIT)
            self.db.commit()
            return db_ingreso

        except (IngresoServiceException, NotFoundException, Exception) as e:
            self.db.rollback()
            if isinstance(e, (IngresoServiceException, NotFoundException)):
                raise e
            raise IngresoServiceException(f"Error fatal durante la anulación de ingreso: {str(e)}")

    # =========================================================================
    # LÓGICA DE LECTURA DE INGRESO
    # =========================================================================
    
    def get_transaccion_ingreso_by_id(self, transaccion_id: int) -> Optional[TransaccionIngresoModel]:
        """Obtiene una transacción de ingreso por su ID."""
        return self.db.query(TransaccionIngresoModel).get(transaccion_id)

    def get_transacciones_ingreso(self, skip: int = 0, limit: int = 100) -> List[TransaccionIngresoModel]:
        """Obtiene una lista paginada de todas las transacciones de ingreso."""
        return self.db.query(TransaccionIngresoModel).offset(skip).limit(limit).all()