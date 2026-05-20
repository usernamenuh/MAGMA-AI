import os
import sys
from setuptools import setup, find_packages
from setuptools.extension import Extension
from Cython.Build import cythonize
import shutil

# --- Configuration ---
# Modules to EXCLUDE from compilation. Your main entry point is a good candidate.
EXCLUDE_MODULES = [
    'main',
    'setup',
    'auth',
    # Exclude all routes files - they use FastAPI decorators
    'routes.',
    # --- CRITICAL ---
    # These scripts are called by the entrypoint and must remain as .py files.
    'core.license_check',
    'core.decrypt_files'
]

# Files to EXCLUDE from post-build cleanup.
EXCLUDE_FROM_CLEANUP = [
    'main.py',
    'setup.py',
    'auth.py',
    'core/run_liscence_lock.sh',
    # --- CRITICAL ---
    # These must also be excluded from cleanup.
    'core/license_check.py',
    'core/decrypt_files.py'
]

# Also preserve all routes files
for root, _, files in os.walk('routes'):
    for file in files:
        if file.endswith('.py'):
            EXCLUDE_FROM_CLEANUP.append(os.path.join(root, file))

# --- End of Configuration ---


def find_python_files(path='.'):
    """Finds all .py files in a directory, respecting exclusions."""
    for root, _, files in os.walk(path):
        for name in files:
            # We are now looking for __init__.py as well
            if name.endswith('.py'):
                module_path = os.path.join(root, name)
                
                # Create a module name like 'openai_local.routes.chat'
                relative_path = os.path.relpath(module_path, '.')
                module_name = os.path.splitext(relative_path.replace(os.path.sep, '.'))[0]
                
                if any(ex in module_name for ex in EXCLUDE_MODULES):
                    print(f"INFO: Excluding module {module_name}")
                    continue
                    
                yield module_path, module_name

def create_extensions():
    """Creates Cython Extension objects for all python files."""
    extensions = []
    for py_path, module_name in find_python_files('.'):
         # Skip files not part of the main application package
        if 'license_tools' not in module_name:
            extensions.append(Extension(module_name, [py_path]))
             
    return extensions

def cleanup(build_dir="build"):
    """Removes original .py files and intermediate .c files after compilation."""
    print("\n--- Starting Cleanup ---")
    deleted_py_count = 0
    deleted_c_count = 0
    
    # Walk the source directory
    for root, _, files in os.walk('.'):
        if 'license_tools' in root:
            continue
            
        for name in files:
            file_path = os.path.join(root, name)
            
            # Use os.path.normpath for consistent path matching across OS
            if any(os.path.normpath(ex) in os.path.normpath(file_path) for ex in EXCLUDE_FROM_CLEANUP):
                continue

            if name.endswith('.py'):
                try:
                    os.remove(file_path)
                    deleted_py_count += 1
                except OSError as e:
                    print(f"Error removing {file_path}: {e}", file=sys.stderr)
            
            if name.endswith('.c'):
                try:
                    os.remove(file_path)
                    deleted_c_count += 1
                except OSError as e:
                    print(f"Error removing {file_path}: {e}", file=sys.stderr)

    print(f"✅ Removed {deleted_py_count} original .py source file(s).")
    print(f"✅ Removed {deleted_c_count} intermediate .c file(s).")

    if os.path.exists(build_dir):
        print(f"✅ Removing '{build_dir}' directory.")
        shutil.rmtree(build_dir)
        
    print("--- Cleanup Complete ---")


# --- Main Setup ---
if __name__ == "__main__":
    is_build_ext = 'build_ext' in sys.argv

    if is_build_ext:
        print("--- Starting Cython Compilation ---")

    setup(
        name="openai_local_secure",
        packages=find_packages(),
        ext_modules=cythonize(
            create_extensions(),
            compiler_directives={'language_level' : "3"},
            exclude_failures=True
        ),
    )

    if is_build_ext:
        cleanup() 