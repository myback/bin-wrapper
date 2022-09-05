from wrappers.exec_wrapper import ExecWrapper
from wrappers.utils import resolve_kubeconfig


class Helm(ExecWrapper):
    """
    helm binary wrapper

    helm = Helm()
    resp = helm.ls(o='json')
    resp.raise_for_status()
    print(resp.json)
    """

    def __init__(self, bin_path: str = 'helm', parent_attrs: list = None, kubeconfig: str = None,
                 namespace: str = None):
        super().__init__(bin_path, parent_attrs)
        self.__parent_attrs = self._ExecWrapper__parent_attrs
        self.__bin = self._ExecWrapper__bin
        self.__namespace = namespace

        self.__kubeconfig = resolve_kubeconfig(kubeconfig)

    def __getattr__(self, item):
        cmd = item.replace('_', '-', -1)

        sub = self.__parent_attrs.copy()
        sub.append(cmd)

        return Helm(self.__bin, sub, kubeconfig=self.__kubeconfig, namespace=self.__namespace)

    def __call__(self, *args, **kwargs):
        self._update_subprocess_params(kwargs)

        cmd_args = [f'--kubeconfig={self.__kubeconfig}']

        namespace = kwargs.get('namespace', kwargs.get('n')) or self.__namespace
        if namespace:
            cmd_args.append(f'--namespace={namespace}')

        parent_args = self.__parent_attrs.copy()
        cmd_args.extend(parent_args)

        for k, v in kwargs.items():
            if not k:
                raise ValueError("empty argument key")

            key = k.replace('_', '-', -1)
            val = str(v)
            if len(k) == 1:
                cmd_args.append(f'-{key}')
                if val:
                    cmd_args.append(val)
            else:
                cmd_args.append(f'--{key}={val}')

        cmd_args.extend(args)

        return self.exec_proc(*cmd_args)
