def slash_join(*args):
    return "/".join(arg.strip("/") for arg in args)
