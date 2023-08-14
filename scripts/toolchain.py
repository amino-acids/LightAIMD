#!/usr/bin/env python3
import os
import sys
import subprocess
from config import *

__all__ = ['setup_toolchain', 'remove_installed_third_parties']

def install_build_tools():
    print("Installing build tools...")
    subprocess.run(["sudo", "apt", "install", "-y", "build-essential", "gfortran", "clang", "ninja-build"], check=True)
    print("Build tools installed")

def find_compilers():
    find_CC()
    find_CXX()
    find_nvcc()

def find_nvcc():
    config['NVCC'] = subprocess.run(['which', 'nvcc'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode('utf-8').strip()
    print(f"NVCC: '{config['NVCC']}'")

    if config['NVCC'] == '':
        print('Warning: nvcc cannot be found, CUDA support is disabled. In order to use CUDA, please set the NVCC environment variable to the path of the nvcc.')
    else:
        print('Info: nvcc found, CUDA support is enabled')
        config['CUDA'] = '-DUSE_CUDA -I/usr/local/cuda/include'
        config['CUDA_LIB'] = '-L/usr/local/cuda/lib64 -lcudart -lcuda'
        config['MODULE_TEST'] += f"{config['CUDA']} {config['CUDA_LIB']}"
        config['NVCC'] += f"-ccbin {config['CC']} --allow-unsupported-compiler -Xnvlink --suppress-stack-size-warning"

    return config['NVCC']

def find_CC():
    config['CC'] = subprocess.run(['which', 'clang'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode('utf-8').strip()
    print(f"CC: '{config['CC']}'")

    if config['CC'] == '':
        print('Critical: C compiler cannot be found')
    #else:
    #    config['CC'] += f" -O3 -Wall {config['CUDA']}"

    return config['CC']

def find_CXX():
    config['CXX'] = subprocess.run(['which', 'clang++'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode('utf-8').strip()
    print(f"CXX: '{config['CXX']}'")

    if config['CXX'] == '':
        print('Critical: C++ compiler cannot be found')
    #else:
    #    config['CXX'] += f" -O3 -Wall {config['CUDA']}"

    return config['CXX']

def create_version_file(data_dir, version):
    with open(os.path.join(data_dir, version), 'w') as f:
        f.write(f"{version}\n")

def check_third_parties(use_cuda=False):
    nlohmann_dir = os.path.join(config['ext_dir'], 'nlohmann')
    nlohmann_version_file = os.path.join(nlohmann_dir, config['NLOHMANN_JSON_VERSION'])
    if not os.path.exists(nlohmann_version_file):
        os.makedirs(nlohmann_dir, exist_ok=True)
        subprocess.run(["wget", f"https://github.com/nlohmann/json/releases/download/v{config['NLOHMANN_JSON_VERSION']}/json.hpp", "-O", os.path.join(nlohmann_dir, "json.hpp")], shell=False, check=True)
        create_version_file(nlohmann_dir, config['NLOHMANN_JSON_VERSION'])
    print('nlohmann json installed')

    eigen_dir = os.path.join(config['ext_dir'], 'eigen')
    eigen_version_file = os.path.join(eigen_dir, config['EIGEN_VERSION'])
    if not os.path.exists(eigen_version_file):
        os.makedirs(config['tmp_dir'], exist_ok=True)
        downloaded_file_path = os.path.join(config['tmp_dir'], f"eigen-{config['EIGEN_VERSION']}.tar.gz")
        subprocess.run(["wget", f"https://gitlab.com/libeigen/eigen/-/archive/{config['EIGEN_VERSION']}/eigen-{config['EIGEN_VERSION']}.tar.gz", "-O", downloaded_file_path], shell=False, check=True)
        subprocess.run(["tar", "xzf", downloaded_file_path, "-C", config['ext_dir']], shell=False, check=True)
        subprocess.run(["mv", os.path.join(config['ext_dir'], f"eigen-{config['EIGEN_VERSION']}"), eigen_dir], shell=False, check=True)
        subprocess.run(["rm", downloaded_file_path], shell=False, check=True)
        create_version_file(eigen_dir, config['EIGEN_VERSION'])
    print('eigen installed')

    libxc_dir = os.path.join(config['ext_dir'], 'libxc')
    libxc_version_file = os.path.join(libxc_dir, config['LIBXC_VERSION'])
    if not os.path.exists(libxc_version_file):
        os.makedirs(config['tmp_dir'], exist_ok=True)
        downloaded_file_path = os.path.join(config['tmp_dir'], f"libxc-{config['LIBXC_VERSION']}.tar.gz")
        subprocess.run(["wget", f"https://gitlab.com/libxc/libxc/-/archive/{config['LIBXC_VERSION']}/libxc-{config['LIBXC_VERSION']}.tar.gz", "-O", downloaded_file_path], shell=False, check=True)
        subprocess.run(["tar", "xzf", downloaded_file_path, "-C", config['tmp_dir']], shell=False, check=True)

        libxc_src_dir = os.path.join(config['tmp_dir'], f"libxc-{config['LIBXC_VERSION']}")
        os.makedirs(libxc_dir, exist_ok=True)

        subprocess.run(["autoreconf", "-i"], cwd=libxc_src_dir, shell=False, check=True)

        if use_cuda:
            subprocess.run([f'CC="/usr/local/cuda/bin/nvcc -x cu -ccbin clang --allow-unsupported-compiler" CFLAGS="--generate-code=arch=compute_80,code=[compute_80,sm_80] --generate-code=arch=compute_70,code=[compute_70,sm_70] -O3 --std=c++14 --compiler-options -Wall,-Wfatal-errors,-Wno-unused-variable,-Wno-unused-but-set-variable" CCLD="/usr/local/cuda/bin/nvcc -ccbin clang --allow-unsupported-compiler" ./configure --enable-cuda --prefix={libxc_dir}'], cwd=libxc_src_dir, shell=True, check=True)
            subprocess.run(["make", "-j", f"{os.cpu_count()}"], cwd=libxc_src_dir, shell=False, check=True)
        else:
            subprocess.run([f"{os.path.join(libxc_src_dir, 'configure')}", f"--prefix={libxc_dir}"], cwd=libxc_src_dir, shell=False, check=True)
            subprocess.run(["make", "-j", f"{os.cpu_count()}"], cwd=libxc_src_dir, shell=False, check=True)

        subprocess.run(["make", "install"], cwd=libxc_src_dir, shell=False, check=True)

        subprocess.run(["rm", downloaded_file_path], shell=False, check=True)
        subprocess.run(["rm", "-rf", libxc_src_dir], shell=False, check=True)
        create_version_file(libxc_dir, config['LIBXC_VERSION'])
    print('libxc installed')

    sto_3g_file = os.path.join(config['root_dir'], 'basis-set', 'sto-3g.json')
    if not os.path.exists(sto_3g_file):
        subprocess.run(["wget", "https://www.basissetexchange.org/api/basis/sto-3g/format/json/", "-O", sto_3g_file], shell=False, check=True)
    print('sto-3g downloaded')

    return 0

def remove_installed_third_parties():
    import shutil
    nlohmann_dir = os.path.join(config['ext_dir'], 'nlohmann')
    eigen_dir = os.path.join(config['ext_dir'], 'eigen')
    libxc_dir = os.path.join(config['ext_dir'], 'libxc')
    sto_3g_file = os.path.join(config['root_dir'], 'basis-set', 'sto-3g.json')

    if os.path.exists(nlohmann_dir):
        shutil.rmtree(nlohmann_dir)
    if os.path.exists(eigen_dir):
        shutil.rmtree(eigen_dir)
    if os.path.exists(libxc_dir):
        shutil.rmtree(libxc_dir)
    if os.path.exists(sto_3g_file):
        os.remove(sto_3g_file)

def setup_toolchain():
    install_build_tools()
    find_compilers()
    check_third_parties(use_cuda=False)

if __name__ == "__main__":
    setup_toolchain()