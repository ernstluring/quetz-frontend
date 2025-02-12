import os
import json
import glob
import shutil
import importlib
import subprocess

import os.path as osp
from pathlib import Path
from itertools import chain
from typing import NoReturn
from typer import Typer, Argument, Option
from setuptools import find_packages
from distutils.spawn import find_executable

from .utils import clean_dir
from .paths import (
    LOCAL_APP_DIR,
    GLOBAL_QUETZ_DIR,
    GLOBAL_FRONTEND_DIR,
    GLOBAL_APP_DIR,
    GLOBAL_EXTENSIONS_DIR
)

app = Typer()

# node ./node_modules/@jupyterlab/builder/lib/build-labextension.js ext_path
# '--core-path core_path' '--static-url static_url' '--development' '--source-map'
# '--watch' '--development' '--source-map'

@app.command()
def link_frontend(
    dev_mode: bool = Option(False, '--development', help="Whether to install it in dev mode or not")
) -> NoReturn:
    """Intall the Quetz-Frontend"""
    assert LOCAL_APP_DIR.exists()

    if not GLOBAL_FRONTEND_DIR.exists() :
        os.mkdir(GLOBAL_FRONTEND_DIR)

    if GLOBAL_APP_DIR.exists() :
        if os.path.islink(GLOBAL_APP_DIR) :
            os.remove(GLOBAL_APP_DIR)
        else:
            shutil.rmtree(GLOBAL_APP_DIR)
    
    if dev_mode :
        os.symlink(LOCAL_APP_DIR, GLOBAL_APP_DIR)
        print(f"""Symlink created:
        Ori:  {LOCAL_APP_DIR}
        Dest: {GLOBAL_APP_DIR}
        """)
    else :
        shutil.copytree(LOCAL_APP_DIR, GLOBAL_APP_DIR, symlinks = True)
        print(f"""App directory copied:
        Ori:  {LOCAL_APP_DIR}
        Dest: {GLOBAL_APP_DIR}
        """)

@app.command()
def clean_frontend() -> NoReturn:
    """Clean the Quetz-Frontend"""
    
    if osp.isfile(GLOBAL_APP_DIR) :
        os.remove(GLOBAL_APP_DIR)
    
    elif osp.islink(GLOBAL_APP_DIR) :
        os.remove(GLOBAL_APP_DIR)

    elif osp.isdir(GLOBAL_APP_DIR) :
        clean_dir(GLOBAL_APP_DIR)
        shutil.rmtree(GLOBAL_APP_DIR)

@app.command()
def install(
    ext_path: str = Argument(Path(), help="The path of the extension")
) -> NoReturn:
    """Build and install an extension"""

    if not GLOBAL_EXTENSIONS_DIR.exists() :
        os.mkdir(GLOBAL_EXTENSIONS_DIR)

    extension_path = Path(osp.realpath(ext_path))
    assert extension_path.joinpath('package.json').exists()

    _build_extension(ext_path, True, False)

    module, metadata = _get_extensions_metadata(extension_path)
    src = Path(extension_path).joinpath(module.__name__, metadata[0]['src'])
    dest = GLOBAL_EXTENSIONS_DIR.joinpath(metadata[0]['dest'])
    
    if osp.isfile(dest) :
        os.remove(dest)
    
    elif osp.islink(dest) :
        os.remove(dest)

    elif osp.isdir(dest) :
        clean_dir(dest)
        shutil.rmtree(dest)
    
    shutil.copytree(src, dest, symlinks = True)
    print(f"""
    Extension installed:
        Path:  {dest}
    """)
    

@app.command()
def develop(
    ext_path: str = Argument(Path(), help="The path of the extension")
) -> NoReturn:
    """Build and install an extension in dev mode"""

    if not GLOBAL_EXTENSIONS_DIR.exists() :
        os.mkdir(GLOBAL_EXTENSIONS_DIR)

    extension_path = Path(osp.realpath(ext_path))
    assert extension_path.joinpath('package.json').exists()

    _build_extension(extension_path, True, False)

    _develop_extension(extension_path)

@app.command()
def build(
    ext_path: str = Argument(Path(), help="The path of the extension"),
    dev_mode: bool = Option(False, '--development', help="Build in development")
) -> NoReturn:
    """Build an extension"""

    if not GLOBAL_EXTENSIONS_DIR.exists() :
        os.mkdir(GLOBAL_EXTENSIONS_DIR)

    extension_path = Path(osp.realpath(ext_path))
    assert extension_path.joinpath('package.json').exists()

    _build_extension(ext_path, dev_mode, False)

@app.command()
def watch(
    ext_path: str = Argument(Path(), help="The path of the extension")
) -> NoReturn:
    """Watch an extension"""

    if not GLOBAL_EXTENSIONS_DIR.exists() :
        os.mkdir(GLOBAL_EXTENSIONS_DIR)

    extension_path = Path(osp.realpath(ext_path))
    assert extension_path.joinpath('package.json').exists()

    _develop_extension(extension_path)
    _build_extension(extension_path, True, True)

@app.command()
def uninstall(
    ext_name: str = Argument("", help="The name of the extension")
) -> NoReturn:
    """Uninstall an extension"""

    if not GLOBAL_EXTENSIONS_DIR.exists() :
        os.mkdir(GLOBAL_EXTENSIONS_DIR)

    extension_path = Path(GLOBAL_EXTENSIONS_DIR, ext_name)
    if osp.isfile(extension_path) :
        os.remove(extension_path)
    
    elif osp.islink(extension_path) :
        os.remove(extension_path)

    elif osp.isdir(extension_path) :
        clean_dir(extension_path)
        shutil.rmtree(extension_path)
    

@app.command()
def list() -> NoReturn:
    """List of extensions"""

    print(f"Installed extensions:")
    print(f"---------------------")
    print(f"  Installation path: '{GLOBAL_EXTENSIONS_DIR}'\n")

    if not GLOBAL_EXTENSIONS_DIR.exists() :
        os.mkdir(GLOBAL_EXTENSIONS_DIR)
        print("No installed extensions yet")
        return
    
    ext_list = os.listdir(GLOBAL_EXTENSIONS_DIR)
    if len(ext_list) == 0 :
        print("No installed extensions yet")
    
    for ext in ext_list :
        print(f"\t-  {ext}")
    
    print()

@app.command()
def clean() -> NoReturn:
    """Clean the extensions directory"""
    if GLOBAL_EXTENSIONS_DIR.exists() :
        clean_dir(GLOBAL_EXTENSIONS_DIR)
        shutil.rmtree(GLOBAL_EXTENSIONS_DIR)

@app.command()
def paths() -> NoReturn:
    """Quetz installation paths"""

    print(f"""
    System cofigured paths:
        Quetz:      {GLOBAL_QUETZ_DIR}
        Frontend:   {GLOBAL_FRONTEND_DIR}
        App:        {GLOBAL_APP_DIR}
        Extensions: {GLOBAL_EXTENSIONS_DIR}
    """)

def _develop_extension(ext_path):
    with open(Path(ext_path, 'package.json')) as fid:
        ext_data = json.load(fid)
    
    _, metadata = _get_extensions_metadata(ext_path)
    src = osp.join(ext_path, ext_data['jupyterlab'].get('outputDir', metadata[0]['src']))
    dest = GLOBAL_EXTENSIONS_DIR.joinpath(ext_data['name'])
    
    if osp.isfile(dest) :
        os.remove(dest)
    
    elif osp.islink(dest) :
        os.remove(dest)

    elif osp.isdir(dest) :
        clean_dir(dest)
        shutil.rmtree(dest)

    os.symlink(src, dest)
    print(f"""
    Symlink created:
        Ori:  {src}
        Dest: {dest}
    """)

def _build_extension(ext_path, dev_mode=False, watch=False):
    if not GLOBAL_APP_DIR.joinpath('package.json').exists():
        print(f"Quetz frontend not fount at '{GLOBAL_APP_DIR}'")

    builder_path = _find_builder(ext_path)
    if builder_path == None :
        print(f"Could not find @jupyterlab/builder at {ext_path}")
        print(f"Extensions require a devDependency '@jupyterlab/builder'")
        return

    exe = 'node'
    exe_path = find_executable(exe)

    if not exe_path:
        print(f"Could not find {exe}. Install NodeJS.")
        exit(1)
    
    command = [
        exe,
        builder_path,
        '--core-path',
        GLOBAL_APP_DIR
    ]

    if dev_mode :
        command.append('--development')
        command.append('--source-map')
    
    if watch :
        command.append('--watch')
        
    command.append(ext_path)

    print("Building extension")
    subprocess.check_call(command)

def _find_builder(ext_path):
    """Find the package '@jupyterlab/builder' in the extension dependencies"""
    
    with open(osp.join(ext_path, 'package.json')) as fid:
        ext_data = json.load(fid)

    depVersion2 = ext_data.get('devDependencies', dict()).get('@jupyterlab/builder')
    depVersion2 = depVersion2 or ext_data.get('dependencies', dict()).get('@jupyterlab/builder')
    if depVersion2 is None:
        return None

    # Find @jupyterlab/builder in the node_modules directory
    target = ext_path
    while not osp.exists(osp.join(target, 'node_modules', '@jupyterlab', 'builder')):
        if osp.dirname(target) == target:
            return None
        target = osp.dirname(target)

    return osp.join(target, 'node_modules', '@jupyterlab', 'builder', 'lib', 'build-labextension.js')

def _get_extensions_metadata(module_path):
    mod_path = osp.abspath(module_path)
    if not osp.exists(mod_path):
        raise FileNotFoundError('The path `{}` does not exist.'.format(mod_path))

    # TODO: Change function name to match lab
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, 'js_plugin_paths') :
            return module, module.js_plugin_paths()
        else :
            module = None
    except Exception:
        module = None

    # Looking for modules in the package
    packages = find_packages(mod_path)
    for package in packages :
        try:
            module = importlib.import_module(package)
            if hasattr(module, 'js_plugin_paths') :
                return module, module.js_plugin_paths()
        except Exception:
            module = None          
            
    raise ModuleNotFoundError('There is not a extension at {}'.format(module_path))

if __name__ == '__main__':
    app()