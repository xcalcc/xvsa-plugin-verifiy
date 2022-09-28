#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


import logging
import os
import sys
import tarfile
import zipfile
import shutil
import json
from stat import S_IXUSR

from common.CommonGlobals import TaskErrorNo
from common.XcalException import XcalException
from common.XcalLogger import XcalLogger
from common.FileUtility import FileUtility


class CompressionUtility:
    ZIP_UNIX_SYSTEM = 3

    def __init__(self):
        pass

    @staticmethod
    def compress_tar_package(logger: XcalLogger, src_location: str, package_path: str, mode="x:gz"):
        """
        Make a tar archive from a file/directory, write to a specific location.
        Support bzip, lzma, gzip (bz2, xz, gz)
        :param logger: Logger of parent
        :param src_location: Directory path
        :param package_path: The output tar archive path
        :param mode: The file mode (x:gz) for GZIP tar "x" for normal tar archive
        :return: None
        """
        with XcalLogger("CompressionUtility", "compress_tar_package", parent=logger):
            if os.path.exists(package_path):
                os.remove(package_path)
            try:
                with tarfile.open(package_path, mode) as t:
                    t.add(src_location, arcname=os.path.basename(src_location), recursive=True)
            except Exception as e:
                logging.exception(e)
                raise XcalException("CompressionUtility", "compress_tar_package", "exception arise in making tarball",
                                    TaskErrorNo.E_COMPRESS_FAIL)

    @staticmethod
    def compress_tar_from_dir(logger: XcalLogger, src_location: str, package_path: str, mode="x:gz"):
        """
        Make a tar archive from a directory, write to a specific location.
        :param logger: Logger of parent
        :param src_location: Directory path
        :param package_path: The output tar archive path
        :param mode: The file mode (x:gz) for GZIP tar "x" for normal tar archive
        :return: None
        """
        with XcalLogger("CompressionUtility", "compress_tar_from_dir", parent=logger):
            if os.path.exists(package_path):
                os.remove(package_path)
            if not os.path.exists(src_location):
                raise XcalException("CompressionUtility", "compress_tar_from_dir", "cannot locate source directory %s" % src_location, TaskErrorNo.E_COMPRESS_FAIL)
            try: 
                with tarfile.open(package_path, mode) as t:
                    t.add(src_location, arcname=".", recursive=True)
            except Exception as e:
                logging.exception(e)
                raise XcalException("CompressionUtility", "compress_tar_from_dir", "tarball creation error",
                                    TaskErrorNo.E_COMPRESS_FAIL)
        pass

    @staticmethod
    def extract_file(logger: XcalLogger, fname: str, dest_dir: str, remove: bool):
        """
        Extract file by zipfile/tarfile
        :param logger:
        :param fname: file to be extracted
        :param dest_dir: extract file to where
        :param remove:
        :return:
        """
        with XcalLogger("CompressionUtility", "extract_file", parent=logger) as log:
            log.info("extracting tar(gz|xz|bz2)/zip", "begin to extract file %s to %s" % (fname, dest_dir))
            if fname.endswith('.tar') or fname.endswith('.tar.gz') or fname.endswith('.tar.bz2') or fname.endswith(
                    '.tar.xz'):
                with tarfile.open(fname) as t:
                    t.extractall(path=dest_dir)
            elif fname.endswith('.zip'):
                with zipfile.ZipFile(fname) as z:
                    # Decompressing each file in the archive
                    for info in z.infolist():
                        extracted_path = z.extract(info, dest_dir)
                        # If source system is UNIX-based and the file is with execution privilege
                        # We should preserve the execution rights on the file extracted.
                        if info.create_system == CompressionUtility.ZIP_UNIX_SYSTEM \
                                and sys.platform != "win32" \
                                and os.path.isfile(extracted_path):
                            unix_attributes = info.external_attr >> 16
                            if unix_attributes & S_IXUSR:
                                os.chmod(extracted_path, os.stat(extracted_path).st_mode | S_IXUSR)

            else:
                raise XcalException("CompressionUtility", "extract_file", "Cannot identify package type",
                                    TaskErrorNo.E_EXTRACT_UNKNOWN_FILEKIND)

            if remove:
                os.remove(fname)

    @staticmethod
    def get_archive(logger: XcalLogger, filename, file_path, input_file=None, destination_path=None):
        """

        :param logger:
        :param filename: xxx.zip file
        :param file_path: where to find the files in the input_file
        :param input_file: contains the files which need to be archived
        :param destination_path:
        :return:
        """
        with XcalLogger("CompressionUtility", "get_archive", parent = logger) as log:
            utility = FileUtility(log)
            if destination_path is not None:
                os.makedirs(destination_path, exist_ok = True)
                utility.goto_dir(destination_path)
            else:
                destination_path = os.getcwd()
                utility.goto_dir(destination_path)

            if filename is None:
                raise XcalException("CompressionUtility", "get_archive", "filename must provided",
                                    TaskErrorNo.E_VARIABLE_MUST_HAVE_VALUE)

            file_path = os.path.normpath(file_path)     # get the canonical file path. will change the \\ to \ on windows system
            if not os.path.exists(file_path):
                raise XcalException("CompressionUtility", "get_archive", "file path %s does not exist" % file_path,
                                    TaskErrorNo.E_SOURCE_DIRECTORY_NOT_EXIST)

            log.info("get_archive ", "begin to archive: %s" % file_path)

            if input_file is None or not os.path.exists(input_file):
                # if input_file(source_files.json) is None or not exists, collect all the files in project_path. For now scan java projects need this.
                filename_without_extension, file_extension = os.path.splitext(filename)
                if file_extension and file_extension.startswith('.'):
                    file_format = file_extension.split('.')[1]
                else:
                    file_format = 'zip'
                archive_file_path = shutil.make_archive(filename_without_extension, file_format, file_path)
            else:
                with open(input_file) as json_file:
                    source_code_files = json.load(json_file)
                    with zipfile.ZipFile(filename, 'w') as source_code_zip:
                        utility.goto_dir(file_path)
                        for source_code_file in source_code_files:
                            if not os.path.exists(source_code_file):
                                log.warn("get_archive ", "source code file %s does not exist" % source_code_file)
                                raise XcalException("CompressionUtility", "get_archive",
                                                    "source code file %s does not exist" % source_code_file,
                                                    TaskErrorNo.E_COMMON_FILE_NOT_EXIST)

                            if source_code_file.startswith(file_path):
                                source_code_zip.write(os.path.relpath(source_code_file, file_path))
                            else:
                                log.warn("get_archive ", "source code file %s does not belongs to project %s" % (source_code_file, file_path))
                        utility.goback_dir()

                archive_file_path = os.path.join(destination_path, filename)
            
            log.info("get_archive ", "archive completed, archive file path: %s" % archive_file_path)

            utility.goback_dir()

            return archive_file_path

    @staticmethod
    def add_dir_to_zip_file(path, zip_file:zipfile.ZipFile):
        """
        Zip the contents of an entire folder (with that folder included
        in the archive). Empty sub-folders will be included in the archive
        as well.
        # zip_file is zipfile handle
        """
        real_root = os.path.abspath(path)
        contents = os.walk(real_root)
        try:
            for root, folders, files in contents:
                # Include all subfolders, including empty ones.
                for folder_name in folders:
                    absolute_path = os.path.join(root, folder_name)
                    relative_path = absolute_path.replace(real_root + os.sep, '')
                    zip_file.write(absolute_path, relative_path)
                for file_name in files:
                    absolute_path = os.path.join(root, file_name)
                    relative_path = absolute_path.replace(real_root + os.sep, '')
                    zip_file.write(absolute_path, relative_path)
        except IOError or OSError or zipfile.BadZipFile as e:
            logging.exception(e)
            raise XcalException("CompressionUtility", "add_dir_to_zip_file", "cannot add the directory to the zip file",
                                err_code=TaskErrorNo.E_UTIL_ZIP_COMPRESS)
        finally:
            zip_file.close()
