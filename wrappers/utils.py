import os
import tempfile


class temp_file:
    def __init__(self, file=None, mode='w', buffering=1, encoding=None, errors=None, newline=None, closefd=True):
        self.__file_name = file
        if not self.__file_name:
            self.__file_name = tempfile.mktemp()

        self.__fd = open(self.__file_name, mode, buffering, encoding, errors, newline, closefd)

    @property
    def name(self):
        return self.__file_name

    def __enter__(self):
        return self.__fd

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__fd is not None:
            self.__fd.close()
            os.remove(self.__file_name)


def resolve_kubeconfig(p: str = None):
    kubeconfig = p or os.getenv('KUBECONFIG')
    if not kubeconfig:
        kubeconfig = os.path.join(os.path.expanduser("~"), '.kube', 'config')

    return kubeconfig
