#!/usr/bin/env python3
"""
Simple script to fix pylint issues without complex sed commands
"""
import os


def fix_trailing_whitespace(filepath):
    """Remove trailing whitespace from a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Remove trailing whitespace from each line
        fixed_lines = [line.rstrip() + '\n' for line in lines]

        # Remove trailing newlines at end of file
        while fixed_lines and fixed_lines[-1].strip() == '':
            fixed_lines.pop()

        # Ensure file ends with exactly one newline
        if fixed_lines and not fixed_lines[-1].endswith('\n'):
            fixed_lines[-1] += '\n'
        elif fixed_lines:
            fixed_lines.append('\n')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

        print(f"Fixed trailing whitespace in: {filepath}")
    except (AttributeError, TypeError, Exception) as e:
        print(f"Error fixing {filepath}: {e}")


def add_pylint_disable(filepath, disable_rules):
    """Add pylint disable comment to top of file if not already present"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        disable_comment = f"# pylint: disable={','.join(disable_rules)}\n"

        # Check if pylint disable already exists
        if '# pylint: disable=' not in content:
            content = disable_comment + content

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"Added pylint disable to: {filepath}")
        else:
            print(f"Pylint disable already exists in: {filepath}")
    except (AttributeError, TypeError, Exception) as e:
        print(f"Error adding pylint disable to {filepath}: {e}")


def find_python_files(directory: str) -> list[str]:
    """Recursively find all Python files in the given directory."""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files


def main():
    print("Fixing pylint issues...")

    # Get the backend directory path (one level up from scripts directory)
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Find all Python files in the backend directory
    python_files = find_python_files(backend_dir)

    print(
        f"Found {len(python_files)} Python files to check for trailing whitespace...")

    # Fix trailing whitespace in all Python files
    for filepath in python_files:
        fix_trailing_whitespace(filepath)


if __name__ == "__main__":
    main()
