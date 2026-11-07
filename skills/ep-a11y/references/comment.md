# PR comment

Step 10 of `SKILL.md`, read only with `--comment` on a PR target, once the report is
final.

Write the full report, ending with the summary block with `commented: true`, to a
temporary file and post one comment:

```bash
gh pr comment <n> --body-file <file>
```

- One comment per run, with no attribution anywhere in it.
- Keep the URL that `gh` prints for the `Posted:` line.
- If posting fails, do not retry: print the report as step 9 describes, with
  `Not posted: <error>` and `commented: false`.

Done when the comment URL is in hand, or the failure is recorded for the report.
