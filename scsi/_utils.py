import ctypes as ct

# the type of `Structure` can be found in the `_ctypes` module, but we
# cannot just import it because the `_ctypes` module does not export
# that type. instead, we can just steal it from the class itself. :D
MetaStructure = type(ct.Structure)


class MetaTypedStructure(MetaStructure):
    def __new__(metacls, name, bases, attrs, **kwargs):
        type_hints = attrs.get("__annotations__", {})
        attrs["_fields_"] = list(type_hints.items())
        return super().__new__(metacls, name, bases, attrs, **kwargs)


class TypedStructure(ct.Structure, metaclass=MetaTypedStructure):
    pass
