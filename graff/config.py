import yaml

_c = {}

def load_config(path=None, **kwargs):
    path = path or 'config.yaml'
    try:
        with open(path) as f:
            _c.update(yaml.load(f))
    except IOError:
        pass
    _c.update(kwargs)

def get(key, default=None):
    return _c.get(key, default)

def setdefault(key, value):
    _c.setdefault(key, value)
