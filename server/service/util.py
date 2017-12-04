

class ServiceException(Exception):

    def __init__(self, user, message):
        name = "%s@%s/%s" % (user['email'], user['domain_id'], user['role_id'])
        message = name + ": " + message
        super(ServiceException, self).__init__(message)

class AudioServiceException(ServiceException):
    pass


class UserServiceException(ServiceException):
    pass

