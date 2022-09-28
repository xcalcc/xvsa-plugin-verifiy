#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


import collections
import json

from common.CommonGlobals import TaskErrorNo
from common.XcalException import XcalException
from common.TokenExtractor import TokenExtractor
from common.XcalLogger import XcalLogger

#
# A Map like ConfigObject which has somewhat similar usage like dict, using get/set methods.
#


class ConfigObject(object):
    def __init__(self, *args):
        """
        :param args: single argument:
            either json string(str)
                   dict
                   ConfigObject (copy)
        """
        if len(args) > 1:
            raise XcalException("ConfigObject", "constructor", "too many parameters, len of args = %d" % len(args),
                                TaskErrorNo.E_CONFIG_PARM_ERROR)
        if len(args) == 1 and isinstance(args[0], str):
            self.raw_config = json.loads(args[0])
        elif len(args) == 1 and isinstance(args[0], dict):
            self.raw_config = args[0].copy()
            self.prune_config()
        elif len(args) == 1 and isinstance(args[0], ConfigObject):
            self.raw_config = args[0].raw_config.copy()
        else:
            self.raw_config = {}

    def __copy__(self):
        return ConfigObject(self.raw_config.copy())

    def get(self, key:str, default:any=None):
        """
        Get value from this configObject
        :param default:
        :param key: the Key to retrieve value of
        :return: value saved or None if nothing is found
        """
        if self.raw_config is not None:
            return self.raw_config.get(key, default)
        return default

    def set(self, key:str, value):
        """
        Set value to the configObject
        :param key: the key to search for the value
        :param value: the value to be saved
        :return: None
        """
        if (isinstance(value, str)):
            self.raw_config[key] = value
        elif isinstance(value, ConfigObject):
            self.raw_config[key] = value
        elif isinstance(value, dict):
            self.raw_config[key] = ConfigObject(value)
        elif isinstance(value, list):
            self.raw_config[key] = value
        else:
            raise XcalException("ConfigObject", "set", "value not acceptable %s" % value,
                                TaskErrorNo.E_UTIL_CONFOBJ_SET)

    def dumps(self):
        return json.dumps(self.convert_to_dict())

    def convert_to_dict(self):
        copy_of_dict = self.raw_config.copy()
        for (key, val) in copy_of_dict.items():
            if isinstance(val, ConfigObject):
                copy_of_dict[key] = val.convert_to_dict()
            elif isinstance(val, dict):
                copy_of_dict[key] = val
            elif isinstance(val, list):
                copy_of_dict[key] = val
            elif isinstance(val, int) or isinstance(val, float):
                copy_of_dict[key] = val
            elif not isinstance(val, str):
                copy_of_dict[key] = str(val)
        return copy_of_dict

    def safe_list(self, val):
        result = []
        for i in val:
            if isinstance(i, str) or isinstance(i, int) or isinstance(i, float):
                result.append(i)
            elif isinstance(i, dict):
                result.append(self.safe_dict_to_dict(i))
            elif isinstance(i, list):
                result.append(self.safe_list(i))
            elif isinstance(i, ConfigObject):
                result.append(self.safe_dict_to_dict(i.convert_to_dict()))
            else:
                raise XcalException("ConfigObject", "safe_list", "value not acceptable i = %s" % str(i),
                                    TaskErrorNo.E_UTIL_CONFOBJ_LIST_CVT)
        pass

    def safe_dict_to_dict(self, val:dict):
        try:
            local_str = json.dumps(val)
        except:
            raise XcalException("ConfigObject", "safe_dict_to_dict", "value to convertible",
                                TaskErrorNo.E_UTIL_CONFOBJ_DICT_CVT)
        else:
            return val.copy()
        pass

    def plain_dict(self):
        return self.raw_config.copy()

    def prune_config(self):
        if self.get("configContent") is not None and isinstance(self.get("configContent"), str):
            str_content = self.get("configContent")
            self.set("configContent", ConfigObject(json.loads(str_content)))

    @staticmethod
    def verify_config(config:dict):
        if not TokenExtractor(config).valid():
            raise XcalException("ConfigObject", "verify_config", "authentication token is missing in request",
                                TaskErrorNo.E_UTIL_CONFOBJ_TOKEN)
        if 'configContent' not in config:
            raise XcalException("ConfigObject", "verify_config", "configContent is missing in request",
                                TaskErrorNo.E_UTIL_CONFOBJ_USERCONTENT)
        if 'scanTaskId' not in config:
            raise XcalException("ConfigObject", "verify_config", "scanTaskId is missing in request",
                                TaskErrorNo.E_UTIL_CONFOBJ_SCANID)
        if 'scanFilePath' not in config:
            raise XcalException("ConfigObject", "verify_config", "scanFilePath is missing in request",
                                TaskErrorNo.E_UTIL_CONFOBJ_SCANFILE)
        if 'preprocessPath' not in config:
            raise XcalException("ConfigObject", "verify_config", "preprocessPath is missing in request",
                                TaskErrorNo.E_UTIL_CONFOBJ_PREPROCPATH)

    @staticmethod
    def merge_two_dicts(x, y):
        """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
        updating only top-level keys, dict_merge recurse down into dicts nested
        to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
        ``dct``.
        :param x: dict onto which the merge is executed, its value is not guaranteed to be in return
        :param y: dct merged into dct, its value will always be in final return
        :return: None
        """
        if x is None:
            x = {}
        if y is None:
            y = {}
        z = x.copy()  # start with x's keys and values
        for k, v in y.items():
            if (k in z and isinstance(z[k], dict)
                    and isinstance(y[k], collections.Mapping)):
                z[k] = ConfigObject.merge_two_dicts(z[k], y[k])
            else:
                z[k] = y[k]
        return z


class UserConfigObject(ConfigObject):
    def __init__(self, user_config:str, raw_config:ConfigObject, logger:XcalLogger):
        super(UserConfigObject).__init__()
        self.raw_config = {}
        user_cfg_json = json.loads(user_config)
        scan_path = raw_config.get('scanFilePath')
        # Replace _SCAN_DIR_ with real value
        logger.info("adjusting config", "... from _SCAN_DIR_ to %s " % scan_path)
        for uctx_key, uctx_val in user_cfg_json.items():
            if isinstance(uctx_val, str) and '_SCAN_DIR_' in uctx_val:
                logger.info("replacing value", ("key:", uctx_key, "org.val:", uctx_val, "new.val", user_cfg_json[uctx_key]))
                self.set(uctx_key, (uctx_val).replace("_SCAN_DIR_", scan_path))
            else:
                self.set(uctx_key, uctx_val)
        return
