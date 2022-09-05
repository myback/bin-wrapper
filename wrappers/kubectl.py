import time

from wrappers.exec_wrapper import ExecWrapper
from wrappers.utils import resolve_kubeconfig


class Kubectl(ExecWrapper):
    """
    kubectl binary wrapper
    k = Kubectl()

    # kubectl get --namespace=kube-system pods
    resp = k.get.pods(namespace='kube-system', o=None)
    if resp.returncode:
        print(f"Call command {' '.join(resp.args)} failed")
        print(resp.stderr)
        sys.exit(resp.returncode)
    else:
        print(resp.stdout)

    # kubectl get -o wide -A pods
    resp = k.get.pods(A=None)
    resp.raise_for_status()
    print(resp.json)

    # kubectl run --image=nginx nginx
    k.run('nginx', image='nginx')

    # kubectl delete --grace-period=0 pod nginx
    k.delete.pod('nginx', grace_period=0)

    # kubectl delete pods --all
    k.delete.pods('--all')

    # kubectl exec -t nginx -- nginx -T
    k.exec('nginx', 'nginx -T')

    # kubectl exec --container=redis --namespace=redis -t zif-redis-master-0 -- redis-cli ping
    k.exec('zif-redis-master-0', 'redis-cli', 'ping', container=redis, namespace=redis)

    # kubectl exec -t nginx -- ls -l /etc/nginx/conf.d
    args = ['ls', '-l', '/etc/nginx/conf.d']
    k.exec('nginx', *args)
    """

    def __init__(self, bin_path: str = 'kubectl', parent_attrs: list = None, *,
                 kubeconfig: str = None, namespace: str = None, output_format: str = 'json'):

        super().__init__(bin_path, parent_attrs)
        self.__parent_attrs = self._ExecWrapper__parent_attrs
        self.__bin = self._ExecWrapper__bin
        self.__namespace = namespace
        self.__out_fmt = output_format

        self.__kubeconfig = resolve_kubeconfig(kubeconfig)

    def __getattr__(self, item):
        cmd = item.replace('_', '-', -1)
        if cmd in ['attach', 'edit', 'port-forward', 'proxy']:
            raise NotImplementedError(f"{item} command not implemented")

        sub = self.__parent_attrs.copy()
        sub.append(cmd)

        return Kubectl(self.__bin, sub, kubeconfig=self.__kubeconfig, namespace=self.__namespace,
                       output_format=self.__out_fmt)

    def __call__(self, *args, **kwargs):
        self._update_subprocess_params(kwargs)

        cmd_args = [f'--kubeconfig={self.__kubeconfig}']

        namespace = kwargs.get('namespace', kwargs.get('n')) or self.__namespace
        if namespace:
            cmd_args.append(f'--namespace={namespace}')

        parent_args = self.__parent_attrs.copy()
        cmd_args.extend(parent_args)

        scale_wait = kwargs.pop('scale_wait', False)
        scale_wait_time = kwargs.pop('scale_wait_time', 180)
        scale_delay = kwargs.pop('scale_delay', 3)

        if parent_args[0] == 'get':
            out_fmt = self.__out_fmt
            if 'o' in kwargs or 'output' in kwargs:
                out_fmt = kwargs.pop('output', kwargs.pop('o', None))

            if out_fmt:
                cmd_args.append(f"--output={out_fmt}")

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

        if parent_args[0] == 'exec':
            cmd_args.extend(['-t', args[0], '--'])
            args = args[1:]

        cmd_args.extend(args)

        resp = self.exec_proc(*cmd_args)
        if resp.return_code:
            return resp

        if scale_wait:
            k = Kubectl()
            func = getattr(k.get, parent_args[1])

            wait = 0
            while 1:
                d = func(*args).json
                if all(map(
                        lambda item: item['status'].get('readyReplicas', 0) == item['spec']['replicas'],
                        d.get('items', [d]))):
                    break

                wait += scale_delay
                if wait >= scale_wait_time:
                    raise TimeoutError("scale of pods")

                time.sleep(scale_delay)

        return resp
