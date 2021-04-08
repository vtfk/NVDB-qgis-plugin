import pathlib
import sys

def install_reqs():
    plugin_dir = pathlib.Path(__file__).parent.parent

    try:
        import pip
    except ImportError:
        exec(
            open(pathlib.Path(plugin_dir, 'get_pip.py')).read()
        )
        import pip
        pip.main(['install', '--upgrade', 'pip'])

    sys.path.append(plugin_dir)
    print(plugin_dir)

    with open(plugin_dir / 'nvdb_qgis_plugin-master' / 'requirements.txt', 'r') as req:
        for dep in req.readlines():
            print(dep)
            dep = dep.strip().split("==")[0]
            try:
                __import__(dep)
            except ImportError as e:
                print("{} ikke tilgjenglig, installing".format(dep))
                pip.main(['install', dep])