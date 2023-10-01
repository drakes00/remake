from remake.builders import gcc, clang

# Compile any .c file into .o file, then compile all .o into target.
rule = PatternRule(deps="%.c", target="%.o", builder=gcc)
Target(rule.allTargets)

# Compile specific .c file into target.
Rule(deps="main.c", targets="main", builder=clang)
Target("main")
