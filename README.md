# py-wrappers
Python wrapper for binary files

## Usage

```python
import wrapper

class Helm(wrapper.ExecWrapper):
    """
    helm binary wrapper

    helm = Helm(o='json')
    resp = helm.ls() => `helm ls -o=json`
    resp.raise_for_status()
    print(resp.json)

    helm = Helm()
    helm.repo.add.bitnami('https://charts.bitnami.com/bitnami')

    helm = Helm()
    resp = helm.upgrade.redis('bitnami/redis', install=None, o='json')
    # helm upgrade redis bitnami/redis --install -o json
    # or same
    resp = helm('upgrade', 'redis', 'bitnami/redis', '--install', o='json')
    # helm upgrade redis bitnami/redis --install -o json
    # or
    resp = helm.upgrade.redis('bitnami/redis', i=None, o='json')
    # helm upgrade redis bitnami/redis -i -o json
    """

    def __init__(self, **kwargs):
        super().__init__('helm', **kwargs)

    def __getattr__(self, item):
        h = Helm(**self._parent_kwargs)
        h._parent_attrs = self._parent_attrs.copy()
        h._parent_attrs.append(item.replace('_', '-', -1))

        return h

    def _pre(self, args, kwargs):
        ns = kwargs.pop('n', None)
        if ns:
            kwargs.setdefault('namespace', ns)
```
