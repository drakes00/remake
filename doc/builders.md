# Builder Class Documentation

The `Builder` class in ReMake is a fundamental component responsible for
defining build actions to be used by rules. It allows developers to specify how
targets should be created from their dependencies, providing flexibility and
extensibility in the build process. By definition, builders are file-agnostic,
generic. Their inputs and outputs are precised by rules.

## Class Definition

```python
class Builder:
    def __init__(self, action, ephemeral=False):
        """
        Initialize the Builder.

        Parameters:
        - `action`: The action to be performed when building the targets.
        - `ephemeral` (optional): If set to `True`, the builder will not be registered, making it suitable for one-time use.
        """
        pass
```

## Features

### 1. Handling Python Functions

Builders can be python functions.
In this case, builder functions are expected to accept three arguments:

- deps: List of `str` containing dependencies;
- targets: List of `str` containing targets to be made;
- console: A `rich` console for logging withing the builder.

```python
def do_some_work(deps, targets, console):
    # Any python code producing `targets` from `deps`.

myBuilder = Builder(action=do_some_work)
Rule(targets="output.txt", deps="input.txt", builder=myBuilder)
AddTarget("output.txt")
```

In this example, a Python function (`do_some_work`) is used as the action for
the builder. The function receives the list of dependencies (`deps`), the list
of targets (`targets`), and a `rich` console (`console`) as arguments.

### 2. Handling Shell Commands

```python
myBuilder = Builder(action=f"touch $@")
Rule(targets="output.txt", builder=myBuilder)
AddTarget("output.txt")
```

Builders can also handle shell commands. In this case, the action is a shell
command to create a file using the `touch` command.

### 3. Handling Automatic Variables ($^, $@)

```python
builder = Builder(action="cp $^ $@")
Rule(targets="output.txt", deps="input.txt", builder=myBuilder)
AddTarget("output.txt")
```

Builders support automatic variables like `$^` (all dependencies), `$<` (first
dependency) and `$@` (all targets). In this example, the builder action copies
the dependencies to the targets.

### 4. Handling Keyword Arguments

```python
def do_some_work(deps, targets, console, myArg=None):
    # Any python code producing `targets` from `deps`.
    # Keyword `myArg` may be used depending on the rule.

myBuilder = Builder(action=do_some_work)
Rule(targets="output.txt", deps="input.txt", builder=myBuilder)
Rule(
    targets="output_with_arg.txt",
    deps="input_with_arg.txt",
    myArg="Some ultra important yet optional information",
    builder=myBuilder
)
AddTarget("output.txt")
```

Builders can handle keyword arguments in the action function. The
`do_some_work` function accepts a keyword argument `myArg`, and the builder is
used in rules with different sets of arguments.
