#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


import re

from scanTaskService.Config import NAME_LEN_MAX


class AgentValueVerifier(object):
    @staticmethod
    def is_name_valid(name:str):
        if name is None or len(name) > NAME_LEN_MAX:
            return False
        return re.match("^[a-zA-Z0-9-_]+$", name) is not None