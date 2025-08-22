#!/usr/bin/env python3
from datetime import date
import os
import re
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

from prompt import FORMAT_GUIDANCE, SYSTEM_PROMPT


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
    parser.add_argument(
        "--output_format",
        required=False,
        default=os.getenv("OUTPUT_FORMAT", "markdown"),
        choices=["markdown", "jekyll", "mkdocs"],
        help="Output style: markdown (default), jekyll, mkdocs",
    )
    return parser.parse_args()


def fetch_release_context_act(event_file: str, openapi_file: str) -> ReleaseContext:
    """
    Load release context from a local GitHub event JSON file (for act mode).
    Safely extracts release info, repository, PRs, issues, and docs URLs.
    """
    with open(event_file, "r") as f:
        event = json.load(f)

    # Safely extract release info
    release = event.get("release") or {}
    release_tag = release.get("tag_name") or "v1.0.0"
    release_body = release.get("body") or ""
    release_name = release.get("name") or f"Release {release_tag}"
    release_url = release.get(
        "html_url",
        f"https://github.com/{event.get('repository', {}).get('full_name', 'example-org/example-repo')}/releases/tag/{release_tag}",
    )

    # Safely extract repository info
    repository = event.get("repository") or {}
    repo_full_name = repository.get("full_name", "example-org/example-repo")

    # Example PRs / issues (act mode doesn’t fetch real PRs)
    pr_titles = [
        pr.get("title", f"Example PR {i+1}")
        for i, pr in enumerate(event.get("pull_requests", []))
    ] or ["Example PR 1", "Example PR 2"]
    pr_descriptions = [pr.get("body", "") for pr in event.get("pull_requests", [])] or [
        "PR body 1",
        "PR body 2",
    ]
    issue_summaries = [issue.get("body", "") for issue in event.get("issues", [])] or [
        "Issue summary example"
    ]

    # OpenAPI diff
    openapi_diff = None
    if openapi_file and Path(openapi_file).exists():
        with open(openapi_file, "r") as f:
            openapi_diff = f.read()

    return ReleaseContext(
        repo=repo_full_name,
        release_tag=release_tag,
        release_notes=release_body,
        pr_titles=pr_titles,
        pr_descriptions=pr_descriptions,
        issue_summaries=issue_summaries,
        openapi_diff=openapi_diff,
        docs_urls=[release_url],
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


def enforce_jekyll_header(text: str, release_tag: str, today: str) -> str:
    """Ensure the Jekyll YAML front matter is present."""
    if text.lstrip().startswith("---"):
        return text
    header = f"""---
layout: post
title: "Release {release_tag} - Highlights"
date: {today}
categories: release
---
"""
    return header + "\n" + text


def generate_blog_post(
    context: ReleaseContext,
    llm_model: str,
    api_key: str,
    llm_url: str,
    output_format: str = "markdown",
    act_mode: bool = False,
) -> BlogPostOutput:

    llm = (
        ChatOpenAI(model=llm_model)
        if not act_mode
        else ChatOllama(
            model=llm_model,
            base_url=llm_url,
        )
    )  # type: ignore

    prompt_template = PromptTemplate(
        template=SYSTEM_PROMPT,
        input_variables=[
            "format_guidance",
            "release_notes",
            "pr_titles",
            "pr_descriptions",
            "issue_summaries",
            "openapi_diff",
            "docs_urls",
            "release_tag",
            "today",
            "repo_url",
        ],
    )

    input_dict = {
        "format_guidance": FORMAT_GUIDANCE.get(
            output_format, FORMAT_GUIDANCE["markdown"]
        ),
        "release_notes": ensure_nonempty(context.release_notes),
        "pr_titles": safe_join(context.pr_titles),
        "pr_descriptions": safe_join(context.pr_descriptions),
        "issue_summaries": safe_join(context.issue_summaries),
        "openapi_diff": ensure_nonempty(context.openapi_diff),
        "docs_urls": safe_join(context.docs_urls),
        "release_tag": context.release_tag,
        "today": date.today().isoformat(),
        "repo_url": f"https://github.com/{context.repo}",
    }

    chain = prompt_template | llm
    response = chain.invoke(input_dict)

    blog_post = response.content.strip()

    # Safety net: enforce Jekyll front matter if needed
    if output_format == "jekyll":
        blog_post = enforce_jekyll_header(
            blog_post, context.release_tag, date.today().isoformat()
        )

    # Optional: fix repo links if LLM replaced release tags incorrectly
    if output_format in ["jekyll", "mkdocs"]:
        blog_post = re.sub(
            r"https://github\.com/[^/]+/[^/]+/releases/tag/[^ \n]+",
            f"https://github.com/{context.repo}/releases/tag/{context.release_tag}",
            blog_post,
        )

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
            output_format=args.output_format,
            act_mode=ACT_MODE,
        )

        # Optionally, write outputs for GitHub Actions
        cleaned_output = (
            output.blog_post
        )
        print(f"BLOG_POST::{cleaned_output}")
        print(f"STATUS::{output.status}")  

    except Exception as e:
        traceback.print_exc()
        print("STATUS::ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
