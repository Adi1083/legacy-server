"""
IND PROJECT Server Engine Version Specification
Authoritative version definitions and release metadata.
"""

__version__ = "1.0.0"
__server_name__ = "IND PROJECT Server"
__protocol_version__ = "1.39.4"
__sub_version__ = "35"
__build_date__ = "2026-11-22"
__author__ = "cook45 & clack"

def get_version_info() -> dict:
    return {
        "version": __version__,
        "server_name": __server_name__,
        "protocol_version": __protocol_version__,
        "sub_version": __sub_version__,
        "build_date": __build_date__,
        "author": __author__,
    }
