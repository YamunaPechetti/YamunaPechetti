#!/usr/bin/env python3
import argparse
import difflib
import json
import re
import sys


def _load_input(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Input must be JSON.") from exc


def _unified_diff(path, before, after):
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
    )


def _extract_trace_file_line(error_text):
    match = re.search(r'File "([^"]+)", line (\d+)', error_text)
    if match:
        return match.group(1), int(match.group(2))
    return None, None


def _extract_generic_file_line(error_text, file_paths):
    for match in re.finditer(r"(\S+):(\d+)", error_text):
        path, line = match.group(1), int(match.group(2))
        if path in file_paths:
            return path, line
    return None, None


def _apply_python_index_error(data):
    error_text = data.get("error", "")
    file_path, line_no = _extract_trace_file_line(error_text)
    if not file_path or not line_no:
        return None, "Cannot safely apply a minimal fix because: no traceback file/line found."
    files = {item["path"]: item["content"] for item in data.get("files", [])}
    if file_path not in files:
        return None, "Cannot safely apply a minimal fix because: source file not provided."
    lines = files[file_path].splitlines()
    if not (1 <= line_no <= len(lines)):
        return None, "Cannot safely apply a minimal fix because: traceback line out of range."
    target_line = lines[line_no - 1]
    match = re.search(r"(\w+)\s*\[\s*(\w+)\s*\]", target_line)
    if not match:
        return None, "Cannot safely apply a minimal fix because: no index access found."
    seq_name, idx_name = match.group(1), match.group(2)
    replacement = f"({seq_name}[{idx_name}] if {idx_name} < len({seq_name}) else None)"
    updated_line = target_line[: match.start()] + replacement + target_line[match.end() :]
    lines[line_no - 1] = updated_line
    updated = "\n".join(lines) + ("\n" if files[file_path].endswith("\n") else "")
    return _unified_diff(file_path, files[file_path], updated), None


def _apply_c_use_after_return(data):
    error_text = data.get("error", "")
    files = {item["path"]: item["content"] for item in data.get("files", [])}
    file_path, line_no = _extract_generic_file_line(error_text, set(files.keys()))
    if not file_path or not line_no:
        return None, "Cannot safely apply a minimal fix because: no error file/line found."
    lines = files[file_path].splitlines()
    if not (1 <= line_no <= len(lines)):
        return None, "Cannot safely apply a minimal fix because: error line out of range."
    target_line = lines[line_no - 1]
    match = re.search(r"return\s*&\s*(\w+)", target_line)
    if not match:
        return None, "Cannot safely apply a minimal fix because: no return-of-address found."
    var_name = match.group(1)
    decl_line_index = None
    for i in range(line_no - 2, -1, -1):
        if re.search(rf"\b{re.escape(var_name)}\b", lines[i]):
            decl_line_index = i
            break
    if decl_line_index is None:
        return None, "Cannot safely apply a minimal fix because: variable declaration not found."
    if lines[decl_line_index].lstrip().startswith("static "):
        return None, "Cannot safely apply a minimal fix because: variable already static."
    lines[decl_line_index] = "static " + lines[decl_line_index].lstrip()
    updated = "\n".join(lines) + ("\n" if files[file_path].endswith("\n") else "")
    return _unified_diff(file_path, files[file_path], updated), None


def generate_fix(data):
    language = (data.get("language") or "").lower()
    error_text = data.get("error", "")
    if language == "python" and "IndexError" in error_text:
        return _apply_python_index_error(data)
    if language in {"c", "c++"} and ("use-after-return" in error_text or "stack-use-after-return" in error_text):
        return _apply_c_use_after_return(data)
    return None, "Cannot safely apply a minimal fix because: unsupported error or language."


def main():
    parser = argparse.ArgumentParser(description="Fix It For Me - minimal diff generator")
    parser.add_argument("-f", "--file", help="Path to JSON input file")
    args = parser.parse_args()
    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    try:
        data = _load_input(text)
    except ValueError as exc:
        print(str(exc))
        sys.exit(1)
    diff, error = generate_fix(data)
    if error:
        print(error)
        sys.exit(1)
    print(diff, end="")


if __name__ == "__main__":
    main()
