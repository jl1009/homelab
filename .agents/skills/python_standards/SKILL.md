---
name: python_standards
description: "Guidelines and rules for writing, editing, and optimizing Python code in the homelab repository."
---

# Python Coding Standards & Token Optimization

Follow these rules whenever writing, editing, or refactoring Python scripts in this repository.

## 1. Type Hints (Python 3.9 Compatible)
* Always include Python 3.9 compatible type annotations for all function/method arguments and return types.
* Because the runtime is Python 3.9.6, do **NOT** use the pipe `|` character for union types (e.g., `str | None` is unsupported at runtime and will crash). 
* Use the built-in `typing` module to import standard PEP 484 type generics:
  * Use `Optional[T]` for fields that can be `None` (e.g., `Optional[str]`).
  * Use `Union[T1, T2]` for multi-type values (e.g., `Union[dict, list]`).
  * Use `Tuple`, `List`, `Dict`, `Any` from `typing` for consistent container type assertions.
* Example:
  ```python
  from typing import Optional, Dict, Tuple
  
  def find_stack(name: str, headers: Dict[str, str]) -> Tuple[Optional[int], Optional[int]]:
      ...
  ```

## 2. Shared Utilities & Code Reuse
* Never duplicate functions. If a function is needed in multiple scripts (e.g., configuring SSL, making HTTP requests, parsing credentials), add/import it from `scripts/utils.py`.
* Ensure scripts import from `utils` using relative or standard path resolutions, accommodating execution from both the repo root and the `scripts/` directory.

## 3. Error Handling and Exceptions
* Do not call `sys.exit()` directly inside helper functions or modules.
* Raise appropriate built-in exceptions (`ValueError`, `RuntimeError`, etc.) or custom exceptions when errors occur.
* Handle user-facing CLI termination (e.g., printing clean errors and calling `sys.exit(1)`) exclusively inside the `if __name__ == "__main__":` entry point of scripts.

## 4. Portability and standard libraries
* Keep dependencies lightweight. Standard libraries are preferred to avoid forcing users to run `pip install` in minimal environments.
* Use the unified `urllib.request` wrappers defined in `scripts/utils.py` to make HTTP calls. This keeps main scripts clean and free of verbose error handling and socket setups.
* Secure defaults: Do not bypass SSL validation by default. If a script supports bypassing SSL (common in homelabs), wrap it in an explicit CLI argument (e.g., `--insecure` or `--no-verify`) rather than hardcoding.
