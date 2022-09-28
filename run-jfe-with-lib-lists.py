#!/usr/bin/env python3
import os, sys, argparse, re, shlex, shutil, enum, hashlib, datetime
import logging
import glob
import logging
import os
import random
import shutil
import tarfile
import tempfile
import json
import shlex
import zipfile

from common.CommandLineUtility import CommandLineUtility
from common.CompressionUtility import CompressionUtility
from common.ConfigObject import ConfigObject
from common.HashUtility import HashUtility
from common.CommonGlobals import TaskErrorNo
from common.FileUtility import FileUtility
from common.XcalException import XcalException
from common.XcalLogger import XcalLogger
from common.CommonGlobals import *

all_args = None
import time
import datetime
import psutil
import subprocess

# Logging
MAX_LOG_DUMP_SIZE = 2000 #In bytes

# JFE Environment variable
CUSTOM_ENV = {"JVM_HEAP": "-Xmx12240m"}

# Performance related
CPU_MAX = 0.8
MEM_FREE_MIN = 10000 #in MB
MEM_FREE_PERCENT = 0.4 # For 32GB memory, 0.3 = 9.6GB, 0.4 = 12.8GB, 0.5 = 16GB
"""
System info with Psutil
"""
 
EXPAND = 1024 * 1024
 
def mems_available():
    ''' Memory '''
    mem = psutil.virtual_memory()
    swap_mem = psutil.swap_memory()
    physical_memory_total = mem.total
    mem_str = " Memory Status:\n"
    mem_str += "   swap total : %d MB\n" % (swap_mem.total / EXPAND)
    mem_str += "   swap free : %d MB\n" % (swap_mem.free / EXPAND)
    mem_str += "   free: %s MB\n" % str(mem.free / EXPAND)
    mem_str += "   total: " + str(physical_memory_total / EXPAND) + " MB\n"
    mem_str += "   used: " + str(mem.used / EXPAND) + " MB\n"
    mem_str += "   available: " + str(mem.available / EXPAND) + " MB\n"
    mem_str += "   available percentage: %d / 100 \n"  % int(mem.available / physical_memory_total * 100)
    logging.info (mem_str)
    if ((mem.available) / (physical_memory_total)) < MEM_FREE_PERCENT :
        return False
    return True
 
 
def cpus_available():
    ''' CPU Info '''
    cpu_str = " CPU Info:\n"
    cpu_status = psutil.cpu_times()
    cpu_str += "   user = " + str(cpu_status.user) + "\n"
    cpu_str += "   system = " + str(cpu_status.system) + "\n"
    cpu_str += "   idle = " + str(cpu_status.idle) + "\n"
    cpu_str += "   used percentage = %d / 100 \n" %  int(cpu_status.user / (cpu_status.idle + cpu_status.user + cpu_status.system))
    logging.info(cpu_str)
    if cpu_status.user / (cpu_status.idle + cpu_status.user + cpu_status.system) > CPU_MAX:
        return False
    return True

def get_system_info_ready():
    if not(mems_available()):  # mem
        return False 
    
    if not(cpus_available())   :
        return False
        # CPU
    return True


class RunMode(enum.Enum):
    Application = 1
    LibraryVtable = 2


# Read the file into an array
def read_file(fn: str):
    all_res = []
    with open(fn, "r") as f:
        # Read list of lines
        while True:
            # Read next line
            line = f.readline()
            # If line is blank, then you struck the EOF
            if not line:
                break
            all_res.append(line.replace("\n", ""))
        pass
    return all_res


def parse_config():
    parser = argparse.ArgumentParser(description="file transformer to convert .W files to .W.ztv and .W.class files")
    # All Arguments
    parser.add_argument("-liblist", "-l", type=argparse.FileType('r'), required=False,
                        help="specify location for lib file")
    parser.add_argument("-dirlist", "-d", type=argparse.FileType('r'), required=False,
                        help="specify location for dir file")
    parser.add_argument("-wholedir", "-w",
                        required=False,
                        help="specify output location")
    parser.add_argument("-jfescript", "-j", type=argparse.FileType('rb'), required=True,
                        help="specify mapfej location")
    parser.add_argument("-timeout", "-t", required=False, default=3600,
                        help="specify timeout duration, in seconds")
    type = argparse.FileType('w')
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    parser.add_argument("-library", action="store_true",
                        help="enable library mode instead of app mode", required=False)
    args = parser.parse_args()
    all_args = args

    return args

class ProcessTimer:
  def __init__(self, command):
    self.command = command
    self.execution_state = False

  def execute(self):
    self.max_vms_memory = 0
    self.max_rss_memory = 0

    self.t1 = None
    self.t0 = time.time()
    CommandLineUtility.bash_execute()
    self.p = subprocess.Popen(self.command,shell=False)
    self.execution_state = True

  def poll(self):
    if not self.check_execution_state():
      return False

    self.t1 = time.time()

    try:
      pp = psutil.Process(self.p.pid)

      #obtain a list of the subprocess and all its descendants
      descendants = list(pp.get_children(recursive=True))
      descendants = descendants + [pp]

      rss_memory = 0
      vms_memory = 0

      #calculate and sum up the memory of the subprocess and all its descendants
      for descendant in descendants:
        try:
          mem_info = descendant.get_memory_info()

          rss_memory += mem_info[0]
          vms_memory += mem_info[1]
        except psutil.error.NoSuchProcess:
          #sometimes a subprocess descendant will have terminated between the time
          # we obtain a list of descendants, and the time we actually poll this
          # descendant's memory usage.
          pass
      self.max_vms_memory = max(self.max_vms_memory,vms_memory)
      self.max_rss_memory = max(self.max_rss_memory,rss_memory)

    except psutil.error.NoSuchProcess:
      return self.check_execution_state()


    return self.check_execution_state()


  def is_running(self):
    return psutil.pid_exists(self.p.pid) and self.p.poll() == None

  def check_execution_state(self):
    if not self.execution_state:
      return False
    if self.is_running():
      return True
    self.executation_state = False
    self.t1 = time.time()
    return False

  def close(self,kill=False):
    try:
      pp = psutil.Process(self.p.pid)
      if kill:
        pp.kill()
      else:
        pp.terminate()
    except psutil.error.NoSuchProcess:
      pass

class CollectDependentBytecodeTasks(object):

    def __init__(self, logger: XcalLogger):
        self.logger = logger

    def run(self, artifact_root:str, tarball_fn:str):
        """
        Collect the result from Maven/Gradle Plugins
        :param global_ctx:
        :param job_config:
        :param step_config:
        :return:
        """
        with XcalLogger("CollectDependentBytecodeTasks", "run", parent=self.logger) as log:

            log.trace("Collect JARs and Class File Folders", {})
            # Scan for result files, i.e., files end with .lib.list and .dir.list
            if not os.path.isdir(artifact_root):
                raise XcalException("CollectDependentBytecodeTasks", "run",
                                    ("Cannot locate the artifact root", "artifact_root = %s" % artifact_root),
                                    TaskErrorNo.E_PRESCAN_RESULT_DIR_NONEXIST)

            all_target_names = set()
            all_dirs_dict = {}
            all_libs_dict = {}
            viable_modules = self.find_modules(all_dirs_dict, all_libs_dict, all_target_names, artifact_root)
            if len(viable_modules) <= 0:
                raise XcalException("CollectDependentBytecodeTasks", "run",
                                    ("Cannot locate any artifact file with root = ", artifact_root,
                                     "please set a viable artifact root to javaArtifactRoot, and javaArtifactPattern"),
                                    TaskErrorNo.E_NO_VIABLE_MIDDLE_RESULT)

            log.trace("Searching for modules completed", ("Viable modules' size =", len(viable_modules)))
            try:
                # Write the entire preprocess.tar.gz file.
                with tarfile.open(tarball_fn, "w:gz") as tf:
                    # Add all libs, with their target/xcalibyte.properties and target/jarfiles
                    for one_lib_path, one_lib_id in all_libs_dict.items():
                        tf.add(one_lib_path,
                               arcname=("%s.dir" + os.sep + "jarfiles" + os.sep + "%s.jar") % (one_lib_id, one_lib_id))
                        self.write_library_properties(one_lib_id, one_lib_path, tf)

                    # Add all modules with their related  target/xcalibyte.properties and target/jarfiles
                    self.add_all_app_modules(all_libs_dict, tf, viable_modules)

                    # Write two global properties files
                    self.write_global_properties(tf, viable_modules)
                pass

            except FileNotFoundError as err:
                raise XcalException("CollectDependentBytecodeTasks", "run",
                                    "Error when collecting library & class files, %s" % str(err),
                                    TaskErrorNo.E_NOT_FOUND_FILE)

            log.trace("Dumping preprocess file complete", ("Archive saved to = ", tarball_fn))

    def find_modules(self, all_dirs_dict: dict, all_lib_dict: dict, all_target_names: set, artifact_root: str):
        """
        Find all modules in the artifact_root that has a
        matching .lib.list/.dir.list file generated
        for each module by plugin, by searching for lists of
        these files and find an intersection between the two.

        The viable_module here indicates that these modules have both files ready.

        :return viable modules in {moduleName: {"libList":..., "dirList": ..., "path": ...}}
        """
        # ------------------------------------
        # Collect all lib files & class dirs from .lib.list and .dir.list
        # ------------------------------------
        candidates_lib = []
        candidates_dir = []
        for root, dirs, files in os.walk(artifact_root):
            for filename in files:
                filepath = os.path.join(root, filename)
                if filepath.endswith(".lib.list"):
                    candidates_lib.append(filepath[:filepath.rfind(".lib.list")])
                elif filepath.endswith(".dir.list"):
                    candidates_dir.append(filepath[:filepath.rfind(".dir.list")])
                pass
            pass
        viable_candidates = [value for value in candidates_dir if value in candidates_lib]
        viable_modules = {}
        if len(candidates_dir) != len(candidates_lib) or len(candidates_lib) != len(viable_candidates):
            self.logger.warn("Find candidates",
                             "Cannot find equal candidates among lib and dir files, "
                             "since len[viable-candidates] = %d, len[candidates-dir] = %d, len[candidates-lib] = %d " %
                             (len(viable_candidates), len(candidates_dir), len(candidates_lib)))

        # ------------------------------------
        # Read entries in libraries and dir lists, into a dict.
        # ------------------------------------
        for one_lib_file in viable_candidates:
            if (os.path.exists(one_lib_file + ".lib.list") and
                    os.path.exists(one_lib_file + ".dir.list")):
                lib_list = read_file(one_lib_file + ".lib.list")
                dir_list = read_file(one_lib_file + ".dir.list")

                for one_lib in lib_list:
                    if all_lib_dict.get(one_lib) is None:
                        one_lib_id = self.get_target_name_from_filepath(all_target_names, one_lib)
                        all_lib_dict[one_lib] = one_lib_id
                        all_target_names.add(one_lib_id)

                in_module_dirs = set()
                for one_dir in dir_list:
                    if all_dirs_dict.get(one_dir) is None:
                        one_dir_id = self.get_target_name_from_filepath(all_target_names, one_dir)
                        all_dirs_dict[one_dir] = one_dir_id
                        in_module_dirs.add(one_dir_id)

                # Saving this module to the module dict
                project_id = self.get_target_name_from_filepath(all_target_names, one_lib_file)
                viable_modules[project_id] = {"libList": lib_list, "dirList": dir_list,
                                              "path": os.path.dirname(one_lib_file), "srcDirList": []}
                pass
            pass
        return viable_modules

    def get_target_name_from_filepath(self, all_target_names: set, one_lib: str):
        """
        Calculate the module's target-name from jar file path or non-jar prefixes
        :param all_target_names:
        :param one_lib:
        :return:
        """
        one_lib_id = os.path.basename(one_lib).replace(".", "-").replace(" ", "")
        while one_lib_id in all_target_names:
            # Conflict in name
            one_lib_id = one_lib_id + "X"
            self.logger.warn("Conflicting names for targets, probably jars", one_lib)
        return one_lib_id

    def add_all_app_modules(self, all_lib_dict: dict, tf: tarfile.TarFile, viable_modules: dict):
        """
        Add all modules with their class-file directories and xcalibyte.properties file into the archive.
        """
        for module_name, module_info in viable_modules.items():
            # Compress the class-file dirs into one Jar.
            with tempfile.NamedTemporaryFile("wb") as prop_f:
                with zipfile.ZipFile(prop_f.name, 'w', zipfile.ZIP_STORED) as zipf:
                    for one_dir in module_info.get("dirList"):
                        CompressionUtility.add_dir_to_zip_file(one_dir, zipf)
                tf.add(prop_f.name, ("%s.dir" + os.sep + "jarfiles" + os.sep + "classes.jar") % module_name)


    def write_library_properties(self, one_lib_id: str, one_lib_path: str, tf: tarfile.TarFile):
        """
        Writing a per-library properties file, marking that it is compile_only and vtable_only
        :return:
        """
        with tempfile.NamedTemporaryFile("w+") as lib_f:
            lib_f.write("version=1.0\n")
            lib_f.write("project=%s\n" % one_lib_id)
            lib_f.write("project_key=%s\n" % one_lib_id)
            lib_f.write("compile_only=true\n")
            lib_f.write("vtable_only=true\n")
            lib_f.write("xc5_root_dir=%s\n" % one_lib_path)
            lib_f.flush()
            tf.add(lib_f.name, ("%s.dir" + os.sep + "xcalibyte.properties") % one_lib_id)
            pass

    def write_global_properties(self, tf:tarfile.TarFile, viable_modules:dict):
        # Write to all-in-one xcalibyte.properties
        with tempfile.NamedTemporaryFile("w+") as tmp:
            # Add a single file
            tmp.write("version=1.0\n")
            tmp.write("project=0000-0000-000000000\n")
            tmp.write("project_key=root\n")
            tmp.write("build_command=mvn.......\n")
            tmp.write("compile_only=false\n")
            tmp.flush()
            tf.add(tmp.name, "java.scan" + os.sep + "xcalibyte.properties")
            tf.add(tmp.name, "xcalibyte.properties")

        # Write to modules.json
        with  tempfile.NamedTemporaryFile("w+") as json_tmp:
            json.dump(viable_modules, json_tmp)
            json_tmp.flush()
            tf.add(json_tmp.name, "modules.json")

def run_one_module(lib_file: str, dir_file: str, run_mode: RunMode, extra_args: list, conf):
    """
    Running one module with JFE
    """
    logger = XcalLogger("run-jfe-with-lib-lists", "run_one_module, with lib: %s, dir : %s" % (lib_file, dir_file))
    lib_list = read_file(lib_file)
    dir_list = read_file(dir_file)

    all_args = []
    jfe_script = conf.jfescript.name
    output_dir = os.path.dirname(lib_file)

    all_args.append(jfe_script)

    if (conf.verbose == True):
        all_args.append("-logLevel=ALL")

    # Application Mode
    if run_mode == RunMode.Application:
        all_args.append("-allow-phantom-refs=true")
        base_name = os.path.basename(lib_file)
        t_base_name = base_name.replace(".lib.list", "") + ".o"
        output_file = os.path.join(output_dir, t_base_name)

        for one_dir in dir_list:
            if not os.path.exists(one_dir):
                raise XcalException("run-jfe", "run_one_module", "class-file dir: '%s' does not exist" % one_dir,
                                    TaskErrorNo.E_VERIFY_LIB_NOT_EXIST)
            all_args.append("-fD," + one_dir)

        for one_lib in lib_list:
            # Lib could be dir or Jar archives.
            if not os.path.exists(one_lib):
                raise XcalException("run-jfe", "run_one_module", "library '%s' does not exist" % one_lib,
                                    TaskErrorNo.E_VERIFY_LIB_NOT_EXIST)
            all_args.append("-cp=" + one_lib)

        all_args.append("-fB," + output_file)

        for one_extra_arg in extra_args:
            all_args.append(one_extra_arg)

        logger.info("application generation", " : " + output_file)
        run_jfe_cmd(all_args, conf)

    # Library V-Table Mode
    elif run_mode == RunMode.LibraryVtable:
        all_args.append("-allow-phantom-refs=true")
        all_args.append("-VTABLE=true")
        all_args.append("-libGenOnly=true")
        all_results = []

        # From XcalAgent.JavaPreScanTask
        all_target_names = set()
        all_dirs_dict = {}
        all_libs_dict = {}

        for one_lib in lib_list:
            if not os.path.exists(one_lib):
                raise XcalException("run-jfe", "run_one_module", "library '%s' does not exist" % one_lib,
                                    TaskErrorNo.E_VERIFY_LIB_NOT_EXIST)

            real_list = all_args.copy()

            base_name = os.path.basename(one_lib)
            if os.path.isdir(one_lib):
                t_base_name = hashlib.md5(one_lib.encode()).hexdigest()
                output_dir = os.path.dirname(lib_file)
                one_lib_output = os.path.join(output_dir, t_base_name + ".o")
                all_results.append(one_lib)
                real_list.append("-fD," + one_lib)
            else:
                t_base_name = base_name.replace(".", "-")
                output_dir = os.path.dirname(lib_file)
                one_lib_output = os.path.join(output_dir, t_base_name + ".o")
                all_results.append(one_lib_output)
                real_list.append("-fC," + one_lib)

            if os.path.exists(one_lib_output):
                continue

            real_list.append("-fB," + one_lib_output)

            logger.info("library generation", " : " + one_lib_output)
            run_jfe_cmd(real_list, conf)
            pass

        lib_output_list_file = lib_file.replace(".lib.list", ".lib.output.list")
        logger.info("writing-object-list", "Writing object list [%d] to : %s" % (len(all_results), lib_output_list_file))
        with open(lib_output_list_file, "w+") as f:
            for line in all_results:
                f.write(line)
                f.write("\n")

# Run JFE with command line list
def run_jfe_cmd(all_args: list, conf):
    logger = XcalLogger("run-jfe-with-lib-lists", "run_jfe_cmd")
    log_file = os.path.join(os.path.abspath(os.curdir), "run-jfe.log")
    timeout = int(conf.timeout)

    trial_times = 0
    while not(get_system_info_ready()) :
        rand_duration = int(random.uniform(10, 200))
        logger.info("system-not-ready", "System resource is not available right now, sleep for %d" % rand_duration)
        time.sleep(rand_duration)
        trial_times += 1
        if (trial_times > 90):
            logger.info("forces-continue", "Tried to wait for 90 cycles, but couldn't wait until system's free. continue anyway")
            break
    
    # Quote all items
    safe_args = []
    for it in all_args:
        safe_args.append(shlex.quote(it))

    # Prepare command line
    cmdline = " ".join(safe_args)
    logger.info("run jfe with options: ", cmdline)
    logger.info("run jfe with timeout: ", timeout)
    logger.info("run jfe with log file: ", log_file)

    custom_env = CUSTOM_ENV.copy()

    envs = dict(os.environ)
    for key, val in custom_env.items():
        envs[key] = val

    # run jfe
    logger.info("start jfe ..", "")
    res = CommandLineUtility.bash_execute(cmdline, timeout=timeout, environment=envs,
                                          logger=logger, logfile=log_file)

    logger.info("jfe  finished ..", " %d " % res)
    if res != 0:
        with open(log_file, "r") as f:
            f.seek(0, 2)
            if (f.tell() > MAX_LOG_DUMP_SIZE):
                f.seek(MAX_LOG_DUMP_SIZE, 2)
            else:
                f.seek(0, 0)
            log_content = f.read()
            logging.error("--------------------------------------------------")
            logging.warning(log_content)
            logging.error("--------------------------------------------------")
        logger.warn("jfe  finished ..", " %d " % res)
        logger.error("run-jfe-with-lib-lists", "run_jfe_cmd", "Please look the log up at file: %s" % log_file)
        raise XcalException("run-jfe-with-lib-lists", "run_jfe_cmd",
                            "mapfej returned non-zero %d .. failed" % res,
                            TaskErrorNo.E_VERIFY_JFE)

def setup_logging():
    work_dir = os.curdir
    logging.getLogger('').handlers = []
    logging.basicConfig(format='[%(asctime)20s]   [%(levelname)10s]  %(message)s', level=log_level)
    logging.addLevelName(XcalLogger.XCAL_TRACE_LEVEL, "TRACE")

    rootLogger = logging.getLogger()
    logFormatter = logging.Formatter('[%(asctime)20s]   [%(levelname)10s]  %(message)s')
    fileHandler = logging.FileHandler(os.path.join(work_dir, "run-jfe-py.log"))
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

def main():
    start_time = datetime.datetime.now()
    setup_logging()

    logging.log(XcalLogger.XCAL_TRACE_LEVEL, "Starting %s on   .... %s" % (__file__, str(start_time)))

    logger = XcalLogger("run-jfe", "main")
    args = parse_config()
    config = args

    if not (args.library):
        runmode = RunMode.Application
    else:
        runmode = RunMode.LibraryVtable

    if (args.wholedir is not None):
        process_whole_dir(args, config, logger)
    elif args.liblist is not None and args.dirlist is not None:
        run_one_module(args.liblist.name, args.dirlist.name, runmode, [], config)


def process_whole_dir(args, config, logger):
    candidates_lib = []
    candidates_dir = []
    for subdir, dirs, files in os.walk(args.wholedir):
        for filename in files:
            filepath = os.path.join(subdir, filename)
            if filepath.endswith(".lib.list"):
                candidates_lib.append(filepath[:filepath.rfind(".lib.list")])
            elif filepath.endswith(".dir.list"):
                candidates_dir.append(filepath[:filepath.rfind(".dir.list")])
            pass
        pass
    viable_candidates = [value for value in candidates_dir if value in candidates_lib]
    if len(candidates_dir) != len(candidates_lib) or len(candidates_lib) != len(viable_candidates):
        logger.warn("find-candidates",
                    "Cannot find adequate candidates since len[candidates-dir] = %d, len[candidates-lib] = %d " %
                    (len(candidates_dir), len(candidates_lib)))
    for one_lib_file in viable_candidates:
        if (os.path.exists(one_lib_file + ".lib.list") and
                os.path.exists(one_lib_file + ".dir.list")):
            run_one_module(one_lib_file + ".lib.list",
                           one_lib_file + ".dir.list", RunMode.Application, [], config)

            run_one_module(one_lib_file + ".lib.list",
                           one_lib_file + ".dir.list", RunMode.LibraryVtable, [], config)


if __name__ == "__main__":
    main()
