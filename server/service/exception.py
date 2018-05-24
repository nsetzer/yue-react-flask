

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