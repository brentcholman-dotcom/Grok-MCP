import os
import json
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("example.env")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")

DEFAULT_ALLOWED_FILE_ROOTS = (Path.cwd(), Path("/private/tmp"), Path("/tmp"))


def _allowed_file_roots() -> tuple[Path, ...]:
    configured = os.getenv("GROK_MCP_ALLOWED_FILE_ROOTS", "")
    if not configured:
        return tuple(root.resolve() for root in DEFAULT_ALLOWED_FILE_ROOTS if root.exists())

    roots = []
    for raw_root in configured.split(os.pathsep):
        if not raw_root:
            continue
        root = Path(raw_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Configured file root is not a directory: {raw_root}")
        roots.append(root)

    if not roots:
        raise ValueError("GROK_MCP_ALLOWED_FILE_ROOTS did not include any usable directories")
    return tuple(roots)


def resolve_allowed_local_file(
    file_path: str | Path,
    allowed_suffixes: set[str] | None = None,
) -> Path:
    path = Path(file_path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"Local path is not a file: {file_path}")

    suffix = path.suffix.lower()
    if allowed_suffixes and suffix not in allowed_suffixes:
        supported = ", ".join(sorted(allowed_suffixes))
        raise ValueError(f"Unsupported file type '{suffix}'. Supported types: {supported}")

    allowed_roots = _allowed_file_roots()
    if not any(path.is_relative_to(root) for root in allowed_roots):
        roots = ", ".join(str(root) for root in allowed_roots)
        raise PermissionError(
            f"Local file access denied for {path}. Configure GROK_MCP_ALLOWED_FILE_ROOTS; "
            f"current allowed roots: {roots}"
        )

    return path


def encode_image_to_base64(image_path: str | Path):
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def encode_video_to_base64(video_path: str | Path):
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    with open(path, "rb") as video_file:
        return base64.b64encode(video_file.read()).decode("utf-8")


def usage_footer(*responses):
    prompt_tokens = completion_tokens = reasoning_tokens = 0
    cost = 0.0
    has_cost = False
    for response in responses:
        usage = response.usage
        if usage:
            prompt_tokens += usage.prompt_tokens
            completion_tokens += usage.completion_tokens
            reasoning_tokens += usage.reasoning_tokens
        if response.cost_usd is not None:
            cost += response.cost_usd
            has_cost = True

    parts = []
    if prompt_tokens or completion_tokens:
        tokens = f"**Tokens:** {prompt_tokens:,} in / {completion_tokens:,} out"
        if reasoning_tokens:
            tokens += f" ({reasoning_tokens:,} reasoning)"
        parts.append(tokens)
    if has_cost:
        parts.append(f"**Cost:** ${cost:.4f}")
    if not parts:
        return ""
    return "\n\n---\n" + " · ".join(parts)

def load_history(session: str):
    path = Path("chats") / f"{session}.json"
    if path.exists():
        return json.loads(path.read_text())
    return []


def save_history(session: str, history: list):
    Path("chats").mkdir(exist_ok=True)
    (Path("chats") / f"{session}.json").write_text(json.dumps(history, indent=2, ensure_ascii=False))


def build_params(**kwargs):
    result = {}
    for key, value in kwargs.items():
        if value:
            result[key] = value
    return result
