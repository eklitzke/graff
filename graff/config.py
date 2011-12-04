_c = {}

def load_config(path=None):
    path = path or 'config.yaml'
    _c.update(yaml.open(path))

def get(key, default=None):
    return _c.get(key, default)
