#
#  Copyright (C) 2019-2020  XC Software (Shenzhen) Ltd.
#


import re


class VersionComparer(object):

    @staticmethod
    def numeric_list_compare(v1, v2):
        coefficient = 1
        if len(v1) < len(v2):
            temp = v1
            v1 = v2
            v2 = temp
            coefficient = -1

        for i in range(len(v1)):
            if len(v2) > i:
                if v1[i] == v2[i]:
                    continue
                elif v1[i] > v2[i]:
                    return coefficient
                else:
                    return -1 * coefficient
            if v1[i] != 0:
                return coefficient

        # Same versions, as 1.0.0 == 1, or 1.08 == 1.8
        return 0

    @staticmethod
    def version_str_compare(version1, version2):
        """
        Compare two versions in . format
        :param version1:
        :param version2:
        :return: 1 if A>B, 0 if A==B, -1 if A<B,
        for example 1 == 1.0.0
        1.1 > 1.0
        1.2 > 1.1.10
        1.10 > 1.2
        """
        return VersionComparer.numeric_list_compare(VersionComparer.normalize(version1), VersionComparer.normalize(version2))

    @staticmethod
    def version_exact_or_range_compare(actual, range_or_exact):
        # if re.search("(.*)->(.*)", one_version):
        #    version_begin = ""
        #    return True
        # else:
        if VersionComparer.version_str_compare(actual, range_or_exact) == 0:
            return True
        else:
            return False

    @staticmethod
    def normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]
