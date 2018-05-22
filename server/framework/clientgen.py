
import os
import sys
from .client import RegisteredEndpoint
from pprint import pformat

def generate_client(app, name="client", outdir="."):

    header = "# This file was auto generated. do not modify\n"
    client_dir = os.path.join(outdir, name)
    if not os.path.exists(client_dir):
        os.makedirs(client_dir)

    py_init = os.path.join(client_dir, "__init__.py")
    open(py_init, "w").close()

    py_endpoints = os.path.join(client_dir, "endpoints.py")
    with open(py_endpoints, "w") as wf:
        wf.write(header)
        wf.write("from .client_impl import RegisteredEndpoint\n")
        wf.write("endpoints = [\n")
        for endpoint in app._registered_endpoints:
            data = endpoint._asdict()
            # stringify function names before formatting.
            if data['body'][0] is not None:
                data['body'] = (data['body'][0].__name__, data['body'][1])
            for i, param in enumerate(data['params']):
                param = list(param)
                param[1] = param[1].__name__
                data['params'][i] = tuple(param)
            endpoint = RegisteredEndpoint(**data)

            f = pformat(endpoint,indent=4, width=70).rstrip()
            wf.write("    %s,\n" % f)
        wf.write("]\n")

    py_client_impl = os.path.join(client_dir, "client_impl.py")
    with open(py_client_impl, "w") as wf:
        wf.write(header)
        with open("server/framework/client.py", "r") as rf:
            wf.write(rf.read())

    # write a cli tool
    py_cli = os.path.join(client_dir, "cli.py")
    with open(py_cli, "w") as wf:
        wf.write(header)
        wf.write("import sys\n")
        wf.write("from .client_impl import generate_argparse, split_auth, Response, AuthenticatedRestClient\n")
        wf.write("from .endpoints import endpoints\n")
        wf.write("def main():\n")
        wf.write("    parser = generate_argparse(endpoints)\n")
        wf.write("    args = parser.parse_args()\n")
        wf.write("    method, url, options = args.func(args)\n")

        wf.write("    username, domain, role = split_auth(args.username)\n")
        wf.write("    password = args.password\n")

        wf.write("    client = AuthenticatedRestClient(args.hostname,\n")
        wf.write("             username, password, domain, role)\n")

        wf.write("    response = Response(getattr(client, method.lower())(\n")
        wf.write("               url, **options))\n")

        wf.write("    for chunk in response.stream():\n")
        wf.write("        sys.stdout.buffer.write(chunk)\n")
        wf.write("    if response.status_code >= 400:\n")
        wf.write("        sys.stderr.write(\"%s\\n\" % response)\n")
        wf.write("        sys.exit(response.status_code)\n")
        wf.write("if __name__ == '__main__':\n")
        wf.write("    main()")

    # write a implementation for a client instance
    py_client = os.path.join(client_dir, "client.py")
    with open(py_client, "w") as wf:
        wf.write(header)
        wf.write("from .client_impl import AuthenticatedRestClient, \\\n")
        wf.write("                         FlaskAppClient\n")
        wf.write("from .endpoints import endpoints\n")

        wf.write("def connect(hostname, username, password, domain=None, role=None):\n")
        wf.write("    client = AuthenticatedRestClient(hostname,\n")
        wf.write("             username, password, domain, role)\n")
        wf.write("    return FlaskAppClient(client, endpoints)\n")