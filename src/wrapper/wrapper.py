from __future__ import annotations

import json
import platform
import shutil
import signal
import subprocess
from pathlib import Path


class ExecWrapper:
    def __init__(self, bin_path: str | Path, *args, **kwargs):
        if not str(bin_path):
            raise RuntimeError('path to executable binary not set')

        if isinstance(bin_path, str):
            bin_path = Path(bin_path)

        if not bin_path.is_absolute():
            abs_bin_path = shutil.which(bin_path)
            if not abs_bin_path:
                raise RuntimeError(f"executable binary {bin_path} not found. Install {bin_path} first")

            bin_path = Path(abs_bin_path)

        self._bin = bin_path
        self._parent_attrs = list(args)
        self._parent_kwargs = kwargs

        self._pfx_char_short = kwargs.pop('prefix_char_short', '-')
        self._pfx_char_long = kwargs.pop('prefix_char_long', '--')

    @property
    def bin_path(self) -> str:
        return str(self._bin.resolve())

    def __getattr__(self, item):
        attrs = self._parent_attrs.copy()
        attrs.append(item.replace('_', '-', -1))

        return ExecWrapper(self._bin, *attrs, **self._parent_kwargs)

    def __call__(self, *args, **kwargs) -> CompletedProcess:
        self._pre(args, kwargs)

        proc_kwargs = {}
        rewrite_parent_kwargs = self._parent_kwargs.copy()
        key_pfx = 'subprocess_'
        for k in list(kwargs.keys()):
            if k.startswith(key_pfx):
                key = k[len(key_pfx):]
                proc_kwargs[key] = kwargs.pop(k)

            if k in rewrite_parent_kwargs:
                rewrite_parent_kwargs[k] = kwargs.pop(k)

        cmd = [str(self._bin)]
        cmd.extend(self.args_from_dict(rewrite_parent_kwargs))
        cmd.extend(self._parent_attrs)
        cmd.extend(args)
        cmd.extend(self.args_from_dict(kwargs))

        proc_kwargs['shell'] = True
        proc_kwargs['text'] = True
        if 'stdin' not in proc_kwargs:
            proc_kwargs['stdin'] = subprocess.PIPE
        if 'stdout' not in proc_kwargs:
            proc_kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in proc_kwargs:
            proc_kwargs['stderr'] = subprocess.PIPE

        return subprocess_run(*cmd, **proc_kwargs)

    def _pre(self, args, kwargs):
        pass

    def args_from_dict(self, data: dict) -> list[str]:
        kw_args = []
        for k, v in data.items():
            if not k:
                continue

            key = k.replace('_', '-', -1)

            pfx, join = (self._pfx_char_short, None) if len(k) == 1 else (self._pfx_char_long, '=')
            flag = [pfx + key]
            if v is not None:
                val = str(v)
                if isinstance(v, bool):
                    val = val.lower()

                flag.append(val)

            if not join:
                kw_args.extend(flag)
            else:
                kw_args.append(join.join(flag))

        return kw_args


def subprocess_run(*cmd, **kwargs):
    timeout = kwargs.pop('timeout', None)
    stream_output = kwargs.pop('stream_output', None)
    if stream_output is not None:
        kwargs['stderr'] = subprocess.STDOUT

    with subprocess.Popen(subprocess.list2cmdline(cmd), **kwargs) as p:
        stdout, stderr = None, None
        if stream_output:
            for line in p.stdout:
                if not line:
                    break

                stream_output(line.replace('\n', ''))
        else:
            try:
                stdout, stderr = p.communicate(None, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                p.kill()
                if platform.system() == 'Windows':
                    exc.stdout, exc.stderr = p.communicate()
                else:
                    p.wait()
                raise
            except:
                p.kill()
                raise

    return CompletedProcess(cmd, p.poll(), stdout=stdout, stderr=stderr)


class CompletedProcess:
    def __init__(self, args, return_code, **kwargs):
        self.args = args
        self.return_code = return_code
        self.stdout = kwargs.pop('stdout', None)
        self.stderr = kwargs.pop('stderr', None)

    @property
    def json(self) -> dict:
        return json.loads(self.stdout)

    def raise_for_status(self):
        if self.return_code:
            raise CompletedProcessError(self.args, self.return_code, stdout=self.stdout, stderr=self.stderr)

    def __repr__(self):
        args = ['args={!r}'.format(self.args),
                'returncode={!r}'.format(self.return_code)]
        if self.stdout is not None:
            args.append('stdout={!r}'.format(self.stdout))
        if self.stderr is not None:
            args.append('stderr={!r}'.format(self.stderr))
        return "{}({})".format(type(self).__name__, ', '.join(args))


class CompletedProcessError(Exception):
    def __init__(self, args, return_code, **kwargs):
        self.args = args
        self.return_code = return_code
        self.stdout = kwargs.pop('stdout', None)
        self.stderr = kwargs.pop('stderr', None)

    def __str__(self):
        if self.return_code and self.return_code < 0:
            try:
                return "Command '%s' died with %r." % (
                    self.args, signal.Signals(-self.return_code))
            except ValueError:
                return "Command '%s' died with unknown signal %d." % (
                    self.args, -self.return_code)
        else:
            stderr = ''
            if self.stderr:
                stderr = '\n' + self.stderr

            return "Command '%s' returned non-zero exit status %d.%s" % (
                self.args, self.return_code, stderr)
