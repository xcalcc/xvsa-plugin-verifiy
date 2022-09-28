#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


import os

from common.CommonGlobals import TaskErrorNo
from common.XcalException import XcalException
from common.XcalLogger import XcalLogger

class FileUtility(object):
    def __init__(self, logger: XcalLogger):
        self.logger = logger
        self.dir_stack = []

    def goback_dir(self):
        """
        Go back one level dir in stack, OS-Independent
        :return: None
        """
        # Reading data back
        if len(self.dir_stack) >= 1:
            last_dir = self.dir_stack.pop()
            self.logger.info("Going back dir_stack", last_dir)
            self.dir_stack.append(os.curdir)
            os.chdir(last_dir)
        else:
            raise XcalException("FileUtility", "goback_dir", "Cannot pop the directory stack",
                                TaskErrorNo.E_FILEUTIL_DIRSTACK)

    def goto_dir(self, new_workdir: str):
        """
        Goto Another dir, while pushing the current dir to stack OS-Independent
        :param new_workdir: str
        :return:  None
        """
        # Reading data back
        self.logger.info("Change working directory", new_workdir)
        self.dir_stack.append(os.path.abspath(os.curdir))
        os.chdir(new_workdir)

    @staticmethod
    def check_dir_exist_readable(dirname):
        if (not os.path.exists(dirname)) or (not os.path.isdir(dirname)):
            raise XcalException("FileUtility", "check_dir_exist_readable",
                                "Dir %s does not exist or is not a valid directory" % dirname,
                                TaskErrorNo.E_COMMON_FOLDER_NONEXIST)

        if not os.access(dirname, os.W_OK | os.R_OK):
            raise XcalException("FileUtility", "check_dir_exist_readable", "Directory %s is not readable/writable" % dirname,
                                TaskErrorNo.E_COMMON_FOLDER_PERMISSION)
        pass