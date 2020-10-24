
"""
Definitions for exceptions thrown by the service layer
"""

class ServiceException(Exception):
    HTTP_STATUS = 400

    def __init__(self, message, status=None):
        super().__init__(message)
        if status is not None:
            self.HTTP_STATUS = status

class AudioServiceException(ServiceException):
    def __init__(self, message, status=None):
        super().__init__(message, status)

class RadioServiceException(ServiceException):
    def __init__(self, message, status=None):
        super().__init__(message, status)

class UserServiceException(ServiceException):
    def __init__(self, message, status=None):
        super().__init__(message, status)

class TranscodeServiceException(ServiceException):
    def __init__(self, message, status=None):
        super().__init__(message, status)

class FileSysServiceException(ServiceException):
    def __init__(self, message, status=None):
        super().__init__(message, status)

class FileSysKeyNotFound(FileSysServiceException):
    def __init__(self, message, status=404):
        super().__init__(message, status)

