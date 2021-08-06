def slash_join(*args):
    """Concatenate the arguments avoiding duplicate slash in the joint"""
    return "/".join(arg.strip("/") for arg in args)
