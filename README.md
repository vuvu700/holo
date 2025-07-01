# holo

`holo` is my **personal utility library**, built over time to centralize and reuse a wide range of tools, functions, and helpers across my projects.  
Whenever I develop a function or module that I find useful in multiple contexts, I add it here.

> ⚠️ **Disclaimer**: This package is **not version-stable**. Breaking changes may occur at any time, and compatibility between versions is not guaranteed.

---

## 📦 About the Project

`holo` is designed to be **modular**, **practical**, and focused on **developer productivity**.  
It includes general-purpose utilities spanning math, cryptography, plotting, profiling, parallelism, file I/O, custom languages, and more.

This repository is not intended to be a public library or a pip-installable package (yet), but rather a **consolidated toolbox** for my personal and experimental projects.

---

## 📂 Modules Overview

Some of the main components include:

| Module/File                   | Description              |
|-------------------------------|--------------------------|
| `prettyFormats.py`            | multiple tools for adavanced text formating of complex objects |
| `profilers.py`                | tool to parse specific region of code/functions |
| `__typing.py` `protocols.py`  | type hinting helpers     |
| `reader.py`                   | util to custom parse (very fast) any file |
| `parallel.py`                 | util for easy multithreading/processing in apps |
| `pointers.py`                 | kinda a pointer in python |
| `ramDiskSave.py`              | tool to temporary store python object on the disk on the fly |
| `jitter.py`                   | numba compilation helper |
| `linkedObjects.py`            | lists, linked lists, history, etc... |
| `logger.py`                   | util to log sys.out/err automaticaly |
| `files.py`                    | files listing or operations |



---

## 🛠️ Development Notes

- Codebase mixes **pure Python** and **Cython** for performance-sensitive parts.
- Internal type definitions are maintained in `__typing.py`.
- The project includes a Cython setup (`compile_cython_setup.py`) to compile C extensions.
- Used extensively in my own projects (tools, experiments, automation).

---

## 🚧 Status

- **Actively evolving** with new ideas, tools, and optimizations.
- Some modules are more stable, others are experimental or prototypes.
- Documentation is sparse, but types and naming aim for clarity.

---

