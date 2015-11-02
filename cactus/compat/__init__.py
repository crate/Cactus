#coding:utf-8

import sys

def total_seconds(td):
    if sys.version_info[:2] >= (2, 7):
        return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6

