import os

from .install_reqs import install_reqs
from qgis.gui import QgsMessageBar

def is_installed():
    if os.path.isfile('install_reqs.py'):
        iface.messageBar().pushMessage("Advarsel!: ", "Installerer nødvendige moduler", level=QgsMessageBar.WARNING, duration=5)
        install_reqs()
        os.rename('install_reqs.py', 'install_reqs_is_installed.py')
    else:
        pass
