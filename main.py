#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from typing import List, Optional

from langchain_ollama import ChatOllama
from github import Github
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import traceback
from pydantic import BaseModel, SecretStr


class ReleaseContext(BaseModel):
    repo: str
    release_tag: str
    release_notes: str
    pr_titles: List[str] = []
    pr_descriptions: List[str] = []
    issue_summaries: List[str] = []
    openapi_diff: Optional[str] = None
    docs_urls: List[str] = []


class BlogPostOutput(BaseModel):
    blog_post: str
    references: List[str] = []
    status: str = "success"


def get_inputs():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--github_token", required=False, default=os.getenv("GITHUB_TOKEN")
    )
    parser.add_argument(
        "--release_tag", required=False, default=os.getenv("RELEASE_TAG", "latest")
    )
    parser.add_argument(
        "--openapi_file",
        required=False,
        default=os.getenv("OPENAPI_FILE", "./openapi.yaml"),
    )
    parser.add_argument(
        "--llm_model", required=False, default=os.getenv("LLM_MODEL", "")
    )
    parser.add_argument(
        "--openai_api_key", required=False, default=os.getenv("OPENAI_API_KEY")
    )
    parser.add_argument("--llm_url", required=False, default=os.getenv("LLM_URL"))
    return parser.parse_args()


def fetch_release_context_act(event_file: str, openapi_file: str) -> ReleaseContext:
    """Use event JSON values for act mode."""
    with open(event_file, "r") as f:
        event = json.load(f)

    release = event.get("release", {})
    repository = event.get("repository", {})

    pr_titles = ["Example PR 1", "Example PR 2"]
    pr_descriptions = ["PR body 1", "PR body 2"]
    issue_summaries = ["Issue summary example"]

    openapi_diff = None
    if openapi_file and Path(openapi_file).exists():
        with open(openapi_file, "r") as f:
            openapi_diff = f.read()

    return ReleaseContext(
        repo=repository.get("full_name", "example-org/example-repo"),
        release_tag=release.get("tag_name", "v1.0.0"),
        release_notes=release.get("body", ""),
        pr_titles=pr_titles,
        pr_descriptions=pr_descriptions,
        issue_summaries=issue_summaries,
        openapi_diff=openapi_diff,
        docs_urls=[
            release.get(
                "html_url",
                "https://github.com/example-org/example-repo/releases/tag/v1.0.0",
            )
        ],
    )


def fetch_release_context_github(
    token: str, release_tag: str, openapi_file: str
) -> ReleaseContext:
    g = Github(token)
    repo = g.get_repo(os.getenv("GITHUB_REPOSITORY", ""))

    if release_tag == "latest":
        release = repo.get_latest_release()
    else:
        release = repo.get_release(release_tag)

    release_notes = release.body or ""
    prs = repo.get_pulls(state="closed", sort="updated", direction="desc")
    pr_titles, pr_descriptions, issue_summaries = [], [], []

    for pr in prs:
        if pr.merged and pr.merged_at > release.created_at:
            pr_titles.append(pr.title)
            if pr.body:
                pr_descriptions.append(pr.body)
            for issue in pr.get_issue_events():
                issue_summaries.append(issue.event)

    openapi_diff = None
    if Path(openapi_file).exists():
        with open(openapi_file, "r") as f:
            openapi_diff = f.read()

    return ReleaseContext(
        repo=repo.full_name,
        release_tag=release.tag_name,
        release_notes=release_notes,
        pr_titles=pr_titles,
        pr_descriptions=pr_descriptions,
        issue_summaries=issue_summaries,
        openapi_diff=openapi_diff,
        docs_urls=[f"{repo.html_url}/releases/tag/{release.tag_name}"],
    )


def ensure_nonempty(value: str | None, placeholder: str = "N/A") -> str:
    """Ensure strings passed to the LLM are non-empty."""
    if value is None or not value.strip():
        return placeholder
    return value


def safe_join(items: list[str], placeholder="N/A") -> str:
    if not items:
        return placeholder
    joined = "\n".join([i for i in items if i and i.strip()])
    return joined if joined.strip() else placeholder


def generate_blog_post(
    context: ReleaseContext,
    llm_model: str,
    api_key: str,
    llm_url: str,
    act_mode: bool = False,
) -> BlogPostOutput:

    llm = (
        ChatOpenAI(model=llm_model, api_key=SecretStr(api_key))
        if not act_mode
        else ChatOllama(
            model=llm_model,
            base_url=llm_url,
        )
    )  # type: ignore

    SYSTEM_PROMPT = """
# Task
You are Octo-Pie-Release-Bot, a technical writer that generates engaging blog posts for developers whenever a new release is published.  
You are given:

1. **Release metadata** (tag, name, notes)  
2. **Pull requests** and **issues** tied to the release  
3. **OpenAPI specification changes** for the API (`openapi.json`)  

Your goal is to create a **public-facing blog post** that highlights what’s new in this release.  

---

# Requirements

- Write in a **developer-friendly but approachable tone**.  
- Summarize the **main improvements** at the top.  
- Highlight **new endpoints**, **changes in error codes**, and **authentication updates**.  
- Include **example request/response snippets** in fenced Markdown code blocks (```json or ```http).  
- Show **before vs. after** examples when relevant (e.g., new error codes).  
- Organize with headings and subheadings.  

---

# Output Format

Produce a **Markdown-formatted blog post** with the following structure:

## Title
Use the release name (e.g. *Octo-Pie API v1.2.0 Released: Authentication & Comments*)  

## Introduction
- High-level summary of the release.  
- What it means for developers.  

## Highlights
- Bullet-point summary of the biggest improvements.  

## New Features
- For each new endpoint in the OpenAPI spec, describe it in plain language.  
- Include a **sample request and response** (from the schema).  

## Improvements & Fixes
- Explain error code changes or improved error handling.  
- Show an example (e.g., `GET /posts/{{id}}` now returns `404` instead of `500`).  

## Closing
- Encourage developers to try out the new endpoints.  
- Mention where to find docs (link to OpenAPI spec if available).


Context:  
Release Notes: {release_notes}  
PR Titles: {pr_titles}  
PR Descriptions: {pr_descriptions}  
Issues: {issue_summaries}  
OpenAPI: {openapi_diff}  
Docs: {docs_urls}  
"""

    prompt_template = PromptTemplate(
        template=SYSTEM_PROMPT,
        input_variables=[
            "release_notes",
            "pr_titles",
            "pr_descriptions",
            "issue_summaries",
            "openapi_diff",
            "docs_urls",
        ],
    )

    input_dict = {
        "release_notes": ensure_nonempty(context.release_notes),
        "pr_titles": safe_join(context.pr_titles),
        "pr_descriptions": safe_join(context.pr_descriptions),
        "issue_summaries": safe_join(context.issue_summaries),
        "openapi_diff": ensure_nonempty(context.openapi_diff),
        "docs_urls": safe_join(context.docs_urls),
    }

    chain = prompt_template | llm
    response = chain.invoke(input_dict)

    blog_post = response.content.strip()
    return BlogPostOutput(
        blog_post=blog_post, references=context.docs_urls, status="success"
    )


def main():
    args = get_inputs()
    try:
        ACT_MODE = os.getenv("ACT", "false").lower() == "true"
        event_file = os.getenv("GITHUB_EVENT_PATH")
        if ACT_MODE:
            if not event_file or not Path(event_file).exists():
                raise ValueError(
                    "ACT_MODE is true but GITHUB_EVENT_PATH is missing or invalid"
                )
            context = fetch_release_context_act(event_file, args.openapi_file)
        else:
            context = fetch_release_context_github(
                args.github_token, args.release_tag, args.openapi_file
            )

        # Generate blog post
        output = generate_blog_post(
            context,
            llm_model=args.llm_model,
            api_key=args.openai_api_key,
            llm_url=args.llm_url,
            act_mode=ACT_MODE,
        )

        # Print the markdown directly
        print(output.blog_post)

        # Optionally, write outputs for GitHub Actions
        cleaned_output = (
            output.blog_post
        )  # .replace('%','%25').replace('\n','%0A').replace('\r','%0D')
        print(f"::set-output name=blog_post::{cleaned_output}")
        print(f"::set-output name=status::{output.status}")

    except Exception as e:
        traceback.print_exc()
        print("::set-output name=status::error")
        sys.exit(1)


if __name__ == "__main__":
    main()
