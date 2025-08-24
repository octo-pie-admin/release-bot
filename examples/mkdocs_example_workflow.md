# MKDocs Example 

## Generate Release + Save + Commit
```yaml
name: Release Bot

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  create_release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout consumer repository
        uses: actions/checkout@v4

      - name: AI-Release-Bot
        id: local_step
        uses: octo-pie-admin/release-bot@bug-cleanup-output
        with:
          github_token: ${{ secrets.TOKEN_GITHUB }}
          llm_model: ${{ secrets.LLM_MODEL || 'llama3.2' }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          release_tag: ${{ github.event.release.tag_name || 'latest' }}
          openapi_file: ${{ secrets.OPENAPI_FILE }}
          output_format: ${{ secrets.OUTPUT_FORMAT || 'mkdocs' }}

      # - name: Debug outputs
      #   run: |
      #     echo "BLOG_POST=${{ steps.local_step.outputs }}"
      #     echo "BLOG_POST=${{ steps.local_step.outputs.blog_post }}"

      - name: Save generated blog post
        run: |
          mkdir -p docs/releases/
          VERSION=${{ github.event.release.tag_name }}
          DATE=$(date +'%Y-%m-%d')
          FILE="docs/releases/${DATE}-release-${VERSION}.md"

          echo "${{ steps.local_step.outputs.blog_post }}" | base64 -d > "$FILE"

          echo "Saved release notes to $FILE"

      - name: Commit and push to main
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"

          git fetch origin main || true
          git checkout main || git checkout -b main origin/main

          # Add new release file(s) under docs/releases/
          git add docs/releases/
          git commit -m "Add release notes for ${{ github.event.release.tag_name }}" || echo "No changes to commit"

          # Rebase onto the latest remote branch to avoid non–fast-forward push issues
          git pull --rebase origin main || true
          git push origin main

```

## Force Deploy MKDocs
```yaml
name: Doc Deploy

# Only trigger, when the build workflow succeeded
on:
    workflow_run:
        workflows: ["Release Bot"]
        types:
            - completed
    workflow_dispatch:

permissions:
  contents: write

jobs:
  doc_deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - name: Configure Git Credentials
        run: |
          git config user.name github-actions[bot]
          git config user.email github-actions[bot]@users.noreply.github.com
      - uses: actions/setup-python@v5
        with:
          python-version: 3.x
      - run: echo "cache_id=$(date --utc '+%V')" >> $GITHUB_ENV 
      - uses: actions/cache@v4
        with:
          key: mkdocs-material-${{ env.cache_id }}
          path: ~/.cache 
          restore-keys: |
            mkdocs-material-
      - run: pip install mkdocs-material 
      - run: mkdocs gh-deploy --force
```

## Learnings

1. Having the deploy inside a separate action forces it to have the latest context of our main branch with the most recent release file.
