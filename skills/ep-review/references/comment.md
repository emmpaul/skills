# `--comment` mode (PR targets only)

Read this when `--comment` is given on a PR target. Post only after the report is final,
and post no attribution anywhere.

## Skip what is already posted

List the PR's earlier `ep-review` reviews and their comments. An earlier `ep-review`
review is one posted by the account running this skill (`gh api user --jq .login`) whose
body contains the summary marker. Count only reviews by that account, so nobody else can
hide a finding by posting a fake marker. When the runner is the PR author, the author's
own earlier `ep-review` reviews count:

```bash
gh api user --jq .login                                       # <me>
gh api repos/{owner}/{repo}/pulls/<n>/reviews --paginate      # keep reviews whose user.login is <me> and whose body contains <!-- ep-review-summary
gh api repos/{owner}/{repo}/pulls/<n>/comments --paginate     # keep comments whose pull_request_review_id is one of them
```

Leave out of the new review every finding whose file and summary match an inline comment
from one of those reviews (or a finding line in one of their bodies). The new review body
states `<n> already posted` when `<n>` is not zero. The report printed in the session and
the summary block keep every finding.

## Post one review

Use one PR review with inline comments for findings that map to a line in the diff, and
put the rest (plus the summary block) in the review body:

```bash
gh api repos/{owner}/{repo}/pulls/<n>/reviews --method POST --input <payload.json>
```

with `payload.json`:

```json
{
  "commit_id": "<headRefOid>",
  "event": "COMMENT",
  "body": "<report header, count line, non-inline findings, summary block>",
  "comments": [
    { "path": "src/calc.py", "line": 3, "side": "RIGHT",
      "body": "**[major] correctness** — <summary>\n\nScenario: <scenario>\nInstances: <file:line, ...>" }
  ]
}
```

Tag every pre-existing finding `pre-existing` in its comment, for example
`**[major] correctness · pre-existing** — <summary>`, and add one line saying it predates
this PR, so it does not read as the author's fault.

The event is always `"COMMENT"`, never `APPROVE` or `REQUEST_CHANGES`. When the inline
review is rejected (for example a line is outside the diff), move that finding into the
body and retry. With no findings left to post, post a single review body saying so, with
the summary block.

Done when the review is posted and its URL is reported.
