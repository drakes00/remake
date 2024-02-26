# Rule and PatternRule Classes Documentation

The `Rule` and `PatternRule` classes in ReMake are fundamental components for
defining named rules and pattern rules. They provide a structured way to specify how
targets are created from their dependencies and offer flexibility in handling
patterns.

## Rule Class

The `Rule` class represents a named build rule with explicit target and
dependency specifications.

### Class Definition

```python
class Rule:
    def __init__(self, targets, deps, builder, name=None):
        """
        Initialize the Rule.

        Parameters:
        - `targets`: The target or list of targets for the rule.
        - `deps`: The dependency or list of dependencies for the rule.
        - `builder`: The associated Builder object defining the build action.
        - `name` (optional): A name for the rule.
        """
        pass
```

### Features

#### 1. Named Rules

```python
fooBuilder = Builder(action="Magically creating $@ from $^")
Rule(targets="output.txt", deps="input.txt", builder=fooBuilder)
```

Named rules allow developers to explicitly specify the targets and dependencies
for a rule. In this example, the builder action is used to create `output.txt`
from `input.txt`.

#### 2. Named Rule Dependencies

```python
fooBuilder = Builder(action="Magically creating $@ from $^")

# Rule with a string as dependencies
Rule(targets="bar", deps="foo", builder=fooBuilder)

# Rule with a list of dependencies
Rule(targets="baz", deps=["foo", "bar"], builder=fooBuilder)
```

Named rule dependencies can be specified as either a string or a list of
strings.

#### 3. Named Rule Targets

```python
fooBuilder = Builder(action="Magically creating $@ from $^")

# Rule with a string as targets
rule = Rule(targets="bar", deps="foo", builder=fooBuilder)

# Rule with a list of targets
rule2 = Rule(targets=["bar", "baz"], deps="foo", builder=fooBuilder)
```

Named rule targets can be specified as either a string or a list of strings.

#### 4. Virtual Targets and Dependencies

```python
pacman = Builder(action="pacman -S $<")

# Rule with virtual target and deps
Rule(deps=[VirtualDep("neovim"), VirtualDep("zsh")], targets=VirtualTarget("init_pkgmgr"), builder=pacman,)

# Virtual target registration
AddVirtualTarget("init_pkgmgr")
```

Dependencies and targets can be set as ``virtual''. This explicitly tells the
`remake` engine to not consider them as files, but as abstract objects. Thus,
no check will be performed on them (dependencies existance, target creation,
last modified date, etc).

## PatternRule Class

The `PatternRule` class represents a build rule with target and dependency
patterns.

### Class Definition

```python
class PatternRule:
    def __init__(self, target, deps, builder, name=None, exclude=None):
        """
        Initialize the PatternRule.

        Parameters:
        - `target`: The target pattern for the rule.
        - `deps`: The dependency pattern or list of dependency patterns for the rule.
        - `builder`: The associated Builder object defining the build action.
        - `name` (optional): A name for the rule.
        - `exclude` (optional): Targets/VirtualTargets to be excluded from pattern matching.
        """
        pass

    def match(self, target):
        """
        Check if the target matches the pattern and return matched dependencies.

        Parameters:
        - `target`: The target to check against the pattern.

        Returns:
        - A list of matched dependencies.
        """
        pass
```

### Features

#### 5. Pattern Rules

```python
fooBuilder = Builder(action="Magically creating $@ from $^")
PatternRule(target="*.bar", deps="*.foo", builder=fooBuilder)
AddTarget("a.bar")
```

Pattern rules provide a way to match and generate targets based on patterns. In
this example, the builder action is applied to create `a.bar` from `a.foo`.

#### 6. Pattern Rules Multiple Dependencies

```python
fooBuilder = Builder(action="Magically creating $@ from $^")

# Simple pattern rule.
PatternRule(target="*.bar", deps="*.foo", builder=fooBuilder)

# Multiple deps pattern rule.
PatternRule(target="*.baz", deps=["*.foo", "*.bar"], builder=fooBuilder)
```

Pattern rule dependencies can be specified as either a string or a list of
strings. Here, the builder action is applied to create `a.baz` from `a.foo` and
`a.bar`.

#### 7. Pattern Rules Exclude Targets

```python
fooBuilder = Builder(action="Magically creating $@ from $^")

# Simple pattern rule with exclude.
PatternRule(target="*.bar", deps="*.foo", builder=fooBuilder, exclude=["a.bar"])

# Multiple deps pattern rule with exclude.
PatternRule(target="*.baz", deps=["*.foo", "*.bar"], builder=fooBuilder, exclude=["a.baz"])
```

Pattern rules can exclude specific targets from matching. Here, `a.bar` and `a.baz` are respectively
excluded from the pattern match, so ReMake will not look for their dependencies.

#### 8. Pattern Rules Produce All Possible Targets

```python
fooBuilder = Builder(action="Magically creating $@ from $<")
rule = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
AddTarget(rule.allTargets)
```

The `allTargets` property of `PatternRule` allows for the generation of all
possible targets based on the pattern using a `glob` call.
