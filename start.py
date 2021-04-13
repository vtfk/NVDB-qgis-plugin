# -*- coding: utf-8 -*-
import sys
import os

#Legger til nvdbapiv3 i enviroment

script_dir = os.path.dirname(__file__)
rel_path_nvdbapi = 'nvdbapi-V3-master'
rel_path_nvdbobjects = 'nvdbobjects.py'
path_nvdbapi = os.path.join(script_dir, rel_path_nvdbapi)
path_nvdbobjects = os.path.join(script_dir, rel_path_nvdbobjects)

if not [k for k in sys.path if 'nvdbapi-V3-master' in k]:
    print('Føyer', path_nvdbapi, 'til søkestien')
    sys.path.append(path_nvdbapi)
    sys.path.append(path_nvdbobjects)
