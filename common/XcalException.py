#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


class XcalException(Exception):
    def __init__(self, service_name: str, operation_name: str, message: any, err_code, hint: str = None, info:dict = None):
        self.service = service_name
        self.operation = operation_name
        self.message = message
        self.err_code = err_code
        self.info = info
        if hint is not None:
            self.hint = hint
        else:
            self.hint = ""
        super(XcalException).__init__()


class XcalExceptionPrinter(object):
    def __init__(self, exception):
        if exception is None or type(exception) is not XcalException:
            self.exception = None
            return
        else:
            self.exception = exception

    def print_error(self):
        print(
            "[ErrNo]:" + self.exception.err_code.__str__() + ", " + "[ErrMsg]:" + self.exception.message + ", " + "[Hint]:" + self.exception.hint)
