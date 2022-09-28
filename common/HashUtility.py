#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


import hashlib
import logging
import os
import zlib


class CRC32(object):
    """
    Wrapper around zlib.crc32 to calculate the crc32 checksum with a similar
    interface as the algorithms in hashlib.
    """
    name = 'crc32'
    digest_size = 4
    block_size = 1

    def __init__(self, arg=None):
        """
        Initialize the class.

        :param arg: String to calculate the digest for.
        """
        self._digest = 0
        if arg is not None:
            self.update(arg)

    def update(self, arg):
        """
        Update the crc32 object with the string arg.  Repeated calls are
        equivalent to a single call with the concatenation of all the arguments:
        m.update(a); m.update(b) is equivalent to m.update(a+b).
        :param arg: String to update the digest with.
        """
        self._digest = zlib.crc32(arg, self._digest) & 0xFFFFFFFF

    def copy(self):
        """
        Return a copy ("clone") of the hash object.  This can be used to
        efficiently compute the digests of strings that share a common initial
        substring.
        """
        copy = CRC32()
        copy._digest = self._digest
        return copy


class HashUtility(object):

    @staticmethod
    def get_crc32_checksum(filename):
        """
        Method for calculating the hash of a file. using crc32 algorithm

        :param filename: Name of the file to calculate the hash for.
        :returns: Digest of the file, in hex.
        """
        crc32 = CRC32()
        chunk_size=4096
        with open(filename, mode="rb", buffering=0) as fp:
            buffer = fp.read(chunk_size)
            while len(buffer) > 0:
                crc32.update(buffer)
                buffer = fp.read(chunk_size)
        return str(crc32._digest)
        #return hex(crc32._digest).upper()[2:]  #return hex value

    @staticmethod
    def get_md5_checksum(filename):
        """
        Get file checksum value.
        Note that sometimes you won't be able to fit the whole file in memory.
        In that case, you'll have to read chunks of 4096 bytes sequentially and feed them to the Md5 function.
        Refer to: https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file

        :param filename: file path
        :return: the digest value as a string of hexadecimal digits
        """
        if not os.path.isfile(filename):
            logging.error("[_get_checksum] %s not found", filename)
            return -1

        if not os.access(filename, os.R_OK):
            logging.error("[_get_checksum] %s cannot be read", filename)
            return -1

        hash_md5 = hashlib.md5()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def get_sha256_hash(filename):
        """
        Get SHA-2 (256bit, in 64bytes hex) hash of a given file, which should be 'rb' readable
        :param filename:
        :return:
        """
        with open(filename, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        return sha

    @staticmethod
    def get_sha1_hash(filename):
        """
        Get SHA-1 (160bit, in 40bytes hex) hash of a given file, which should be 'rb' readable
        :param filename:
        :return:
        """
        with open(filename, "rb") as f:
            sha = hashlib.sha1(f.read()).hexdigest()
        return sha
