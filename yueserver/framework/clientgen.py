
"""
Client Package Generator

generate a python package which implements both an Argument Parser and
a RESTful client which can communicate with the given application.
"""
import os
import sys
from .client import RegisteredEndpoint
from pprint import pformat

def generate_client(app, name="client", outdir="."):
    """
    generate a client python package
    """

    header = "# This file was auto generated. do not modify\n"
    client_dir = os.path.join(outdir, name)
    if not os.path.exists(client_dir):
        os.makedirs(client_dir)

    py_init = os.path.join(client_dir, "__init__.py")
    open(py_init, "w").close()

    py_endpoints = os.path.join(client_dir, "endpoints.py")
    with open(py_endpoints, "w") as wf:
        wf.write(header)
        wf.write("from .client import RegisteredEndpoint, Parameter\n")
        wf.write("endpoints = [\n")
        for endpoint in app._registered_endpoints:
            f = pformat(endpoint, indent=4, width=70).rstrip()
            wf.write("    %s,\n" % f)
        wf.write("]\n")

    py_client_impl = os.path.join(client_dir, "client.py")
    with open(py_client_impl, "w") as wf:
        wf.write(header)
        with open("yueserver/framework/client.py", "r") as rf:
            wf.write(rf.read())

    py_endpoints = os.path.join(client_dir, "connect.py")
    with open(py_endpoints, "w") as wf:
        wf.write(header)
        wf.write("from .client import connect_impl\n")
        wf.write("from .endpoints import endpoints\n\n")
        wf.write("def connect(host, username, password):\n")
        wf.write("    return connect_impl(host, username, password, endpoints)\n")

    # write a cli tool
    py_cli = os.path.join(client_dir, "cli.py")
    with open(py_cli, "w") as wf:
        wf.write(header)
        wf.write("import sys\n")
        wf.write("from .client import cli_main as main\n")
        wf.write("from .endpoints import endpoints\n")
        wf.write("if __name__ == '__main__':\n")
        wf.write("    main(endpoints, sys.argv[1:])\n")



