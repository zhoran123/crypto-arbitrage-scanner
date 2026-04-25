"""Fast JSON parser shared by hot-path WS connectors. Falls back to stdlib json
when orjson is unavailable so dev environments without C extensions still run."""

try:
    import orjson as _orjson

    def loads(raw):
        return _orjson.loads(raw)

    def dumps(obj) -> str:
        return _orjson.dumps(obj).decode("utf-8")

except ImportError:
    import json as _json

    def loads(raw):
        return _json.loads(raw)

    def dumps(obj) -> str:
        return _json.dumps(obj)
