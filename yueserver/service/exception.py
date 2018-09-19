
"""
Definitions for exceptions thrown by the service layer
"""

class ServiceException(Exception):
    pass

class AudioServiceException(ServiceException):
    pass

class UserServiceException(ServiceException):
    pass

class TranscodeServiceException(ServiceException):
    pass

class FileSysServiceException(ServiceException):
    pass