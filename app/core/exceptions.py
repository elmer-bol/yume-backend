# Archivo: app/core/exceptions.py
# Este archivo define las excepciones personalizadas para una gestión de errores limpia y centralizada.

class AppBaseException(Exception):
    """Clase base para todas las excepciones de la aplicación."""
    def __init__(self, detail: str = "Ocurrió un error inesperado en la aplicación."):
        self.detail = detail
        super().__init__(self.detail)

# Excepciones de la Capa de Base de Datos (DB)
class DBServiceException(AppBaseException):
    """Excepción para errores de base de datos o transacciones."""
    pass

class NotFoundException(DBServiceException):
    """Excepción lanzada cuando un recurso no es encontrado (HTTP 404)."""
    def __init__(self, resource_name: str = "Recurso"):
        super().__init__(detail=f"{resource_name} no encontrado(a).")

class DuplicateEntryException(DBServiceException):
    """Excepción lanzada cuando se intenta crear un registro duplicado."""
    pass

# Excepciones de la Capa de Servicio/Lógica de Negocio
class AuthenticationException(AppBaseException):
    """Excepción para problemas de autenticación o credenciales inválidas."""
    pass

class AuthorizationException(AppBaseException):
    """Excepción para problemas de permisos o acceso."""
    pass

class IngresoServiceException(AppBaseException):
    """Excepción para errores específicos durante la lógica del servicio de Ingresos."""
    pass