#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


TOKEN_FIELD_NAME = "token"


class TokenExtractor(object):
    def __init__(self, config):
        self.config = config
        pass

    def get_token_str(self):
        return 'Bearer %s' % self.config.get("token")

    def get_xvsa_token(self):
        return self.config.get("token")

    def get_plain_token(self):
        return self.config.get("token")

    def valid(self):
        return self.config.get("token") is not None


class TokenInjector(object):
    def __init__(self, config:dict, task_config):
        self.config = config.copy()
        self.config["token"] = TokenExtractor(task_config).get_plain_token()

    def get_injected(self):
        return self.config


class TokenObjectCreator(object):
    def __init__(self):
        pass

    def inject_object(self, config:dict, token:str):
        config["token"] = token
        return config
