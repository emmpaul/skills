# Known findings file (`--known`)

Read this when `--known <file>` is given. The file holds one finding per line, in the form
callers already write:

```
finding: <id> <dimension> <severity> <file>:<line> | <summary> | <scenario>
```

The leading `finding: ` and the trailing `| <scenario>` are optional. After the scenario,
a line may add `| class: <label>` and `| instances: <file>:<line>,<file>:<line>` (the
finding's class and other locations, as the report prints them). Callers may keep other
lines in the same file (`ep-orchestrate` writes a round label such as `2` or `g3` and
`commits:` lines).

A line is a finding line when it starts with `finding:`, or when its second word is a
dimension (`correctness`, `spec`, `tests`, `security`). Skip every other line, blank lines
included, silently. Count a finding line that does not fit the form as unreadable and
leave it out; the report says how many (SKILL.md step 6).

What happens to the known findings that do parse is in SKILL.md: they become verification
candidates in step 4, are checked as `fixed` or `still open` in step 5, and are reported
and counted in step 6.
