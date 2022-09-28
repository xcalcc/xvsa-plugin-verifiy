#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


import os
import subprocess
import tempfile
import time

from common.CommonGlobals import TaskErrorNo
from common.XcalException import XcalException
from common.XcalLogger import XcalLogger


class CommandLineUtility(object):

    @staticmethod
    def bash_execute(command:str, timeout:float, logger:XcalLogger, logfile:str = None, environment:dict = None,
                     need_display:bool = True):
        """
        Invoke the shell/command line utility to execute command,
                    which may need proper privileges
        :param command:  command line to execute, please consider Windows / Linux capabilities
        :param timeout:  timeout, in seconds
        :param logfile:  file name to the log file of the process, may be a tempfile.NamedTemporaryFile or
                         any file name with write privilege
        :param logger:    XcalLogger
        :param environment: environment variables to pass down.
        :param need_display: whether to display the output of the subprocess to logs/screen
        :return: (int) the return code from the subprocess.
        """
        with XcalLogger("CommandLineUtility", "bash_execute", parent=logger) as log:
            out_fn = logfile
            tempfile_used = False

            if environment is None:
                environment = dict(os.environ)

            if out_fn is None:
                local_temp_file = tempfile.NamedTemporaryFile(mode="w+b")
                out_fn = local_temp_file.name
                tempfile_used = True

            log.info("execution command", command)
            log.info("dump to file", ("file name :", out_fn))

            # Invoking Process --------------------------
            with open(out_fn, "a+b") as out_f:
                out_f.write("\n---- execution command ------ \n".encode("UTF-8"))
                out_f.write(str(command).encode("UTF-8"))
                out_f.write(("\n----- saving dump to file -----\n" + out_fn).encode("UTF-8"))
                out_f.write("\n----- environment: -----\n".encode("UTF-8"))
                out_f.write(str(environment).encode("UTF-8"))
                out_f.write("\n-------------------\n".encode("UTF-8"))
                out_f.flush()

                if timeout is not None:
                    endtime = time.monotonic() + timeout

                process = subprocess.Popen(command, shell = True, universal_newlines = True, stdout = subprocess.PIPE,
                                           stderr = subprocess.STDOUT,
                                           env = environment)
                while True:
                    line = process.stdout.readline()
                    if line == '' and process.poll() is not None:
                        break
                    if need_display and line:
                        log.trace("[output]", line.strip())
                    CommandLineUtility._check_timeout(endtime, timeout)

                rc = process.poll()
                out_f.write(("execution command return code: %s\n" % rc).encode("UTF-8"))

            if tempfile_used:
                local_temp_file.close()

            log.trace("subprocess return code: ", rc)
            return rc

    @staticmethod
    def _check_timeout(endtime, orig_timeout):
        """Convenience for checking if a timeout has expired."""
        if endtime is None:
            return
        if time.monotonic() > endtime:
            raise XcalException("CommandLineUtility", "_check_timeout", "timeout: %s" % orig_timeout,
                                TaskErrorNo.E_COMMON_TIMEOUT)
