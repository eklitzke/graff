import yaml

_c = {}

def load_config(path=None):
    path = path or 'config.yaml'
    try:
        with open(path) as f:
            _c.update(yaml.load(f))
    except IOError:
        pass

def get(key, default=None):
    return _c.get(key, default)
