# Fix It For Me

Minimal, rule-based diff generator for common developer errors.

## Usage

Input is JSON via stdin or `--file`, output is a unified diff to stdout.

```json
{
  "language": "python",
  "error": "Traceback (most recent call last):\n  File \"app.py\", line 3, in <module>\n    value = items[idx]\nIndexError: list index out of range",
  "files": [
    {
      "path": "app.py",
      "content": "items = [1, 2]\nidx = 5\nvalue = items[idx]\n"
    }
  ]
}
```

```bash
python fixit.py --file input.json
```

## MVP Support

- Python IndexError (list index out of range)
- C/C++ use-after-return (address of stack returned)

## Example Output (Python IndexError)

```diff
--- app.py
+++ app.py
@@
-value = items[idx]
+value = (items[idx] if idx < len(items) else None)
```

## Example Output (C use-after-return)

```json
{
  "language": "c",
  "error": "ERROR: AddressSanitizer: stack-use-after-return in main (example.c:7)",
  "files": [
    {
      "path": "example.c",
      "content": "int *make_ptr(void) {\n    int value = 1;\n    return &value;\n}\n"
    }
  ]
}
```

```diff
--- example.c
+++ example.c
@@
-    int value = 1;
+    static int value = 1;
```
