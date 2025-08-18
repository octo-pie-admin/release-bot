# 🐙 Octo-Pie Release Bot

> Automated release blogs, served fresh 🍰

**Octo-Pie Release Bot** is a GitHub Action that turns your release notes, PRs, and OpenAPI specs into polished blog posts.  
It helps open source projects and teams **drive adoption & awareness**—while letting engineers focus on shipping code, not writing copy.

---

## ✨ Features
- 🔖 Automatically generate a blog post for each release
- 📦 Pulls context from release notes, PRs, RFCs, and OpenAPI specs
- 📝 Outputs clean markdown ready to publish
- 🚀 Keeps your docs & blog fresh without marketing overhead

---

## 📦 Installation

Add **Octo-Pie Release Bot** to your repo as a GitHub Action.

1. Create (or update) `.github/workflows/release-blog.yml`
2. Copy in the example workflow below
3. Commit & push 🚀

---

## ⚙️ Example Workflow

```yaml
name: Generate Release Blog Post

on:
  release:
    types: [published]

jobs:
  generate-blog:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Octo-Pie Release Bot
        uses: your-org/release-bot@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          release_tag: ${{ github.event.release.tag_name }}
          openapi_file: "./openapi.yaml"
          llm_model: "gpt-4o-mini"

      - name: Save generated blog post
        run: |
          echo "${{ steps.run.outputs.blog_post }}" > blog/generated-post.md
```

## 🛠 Inputs
* Name	Required	Default	Description
* github_token	✅	—	GitHub token with repo scope
* release_tag	❌	latest release	Release tag to summarize
* openapi_file	❌	./openapi.yaml	Path to OpenAPI file
* llm_model	❌	gpt-4o-mini	LLM model to use via LangChain

## 📤 Outputs
Name	Description
blog_post	Generated markdown blog post
status	Pipeline status (success or error)

## 🍰 Example Output
After a release, Octo-Pie will generate a markdown file like:

```markdown
# 🚀 Release v1.2.0

This release introduces major improvements to our API:

- New `/users/{id}/activity` endpoint for analytics  
- Performance optimizations in database queries  
- Fixes for authentication edge cases  

**Why it matters:**  
Developers can now track user behavior in real-time, with faster responses and improved reliability.


[View full docs →](./openapi.yaml)
```

# 🛣️ Roadmap

Octo-Pie-Release-Bot is **100% free and open source** under the MIT license.  
Our goal is to help projects automate their release notes and blog posts, so engineers can focus on shipping.

## What’s Next
- 🔌 Extra integrations (Slack, Notion, LinkedIn publishing)
- 🎨 Customization (brand voice, multi-language support, templates)
- ☁️ More supported models
