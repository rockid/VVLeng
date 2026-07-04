"""
Three-layer config loader.

Loads .env (secrets) + config.yaml (shared defaults) + clients/{client_id}.yaml
and merges into a single AppConfig dataclass used by all downstream modules.

Usage:
    from config_loader import load_config
    config = load_config(client_id_override="Joinee")
"""

import os
import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# ── Dataclasses ────────────────────────────────────────────────────────────


@dataclass
class ActorConfig:
    post_search: str = "harvestapi/linkedin-post-search"
    post_scraper: str = "harvestapi/linkedin-post-search"
    profile_scraper: str = ""   # deprecated — no longer available on Apify
    follower_scraper: str = ""  # deprecated


@dataclass
class LLMConfig:
    comment_model: str = "gpt-4.1-mini"
    hook_model: str = "gpt-4.1-mini"
    signal_model: str = "gpt-4.1-mini"
    scoring_model: str = "gpt-4.1-mini"

    # Populated from .env (secrets)
    api_key: str = ""
    base_url: str = ""


@dataclass
class DefaultsConfig:
    max_posts_per_keyword: int = 50
    min_post_length_chars: int = 100
    max_post_age_days: int = 7
    dedup_window_days: int = 14
    apify_max_runs_per_hour: int = 10
    fetch_usage_after_run: bool = False


@dataclass
class PathsConfig:
    clients_dir: str = "./clients"
    data_dir: str = "./data"
    logs_dir: str = "./logs"

    # Derived (set after client is known)
    client_data_dir: str = ""


@dataclass
class NicheConfig:
    product_description: str = ""
    primary_use_case: str = ""
    expanding_use_cases: list[str] = field(default_factory=list)
    target_audience: list[str] = field(default_factory=list)
    pain_vocabulary: list[str] = field(default_factory=list)


@dataclass
class ClientCollectionConfig:
    posts_per_keyword: int = 30
    min_engagement_tier1: int = 10
    min_engagement_tier2: int = 50
    min_engagement_tier3: int = 5
    graph_traversal_enabled: bool = False


@dataclass
class ClientFilterConfig:
    min_semantic_similarity: float = 0.75
    blocked_substrings: list[str] = field(default_factory=list)


@dataclass
class ClientScoringConfig:
    tier_a_threshold: float = 0.65
    tier_b_threshold: float = 0.40
    influencer_follower_threshold: int = 5000
    min_score_for_signal: int = 6
    # Minimum composite post score required to qualify as a comment_target.
    # Raise it to make the shortlist more selective.
    min_comment_target_score: float = 0.40


@dataclass
class ClientActionLimitsConfig:
    connections_per_day: int = 15
    comments_per_day: int = 8
    visits_per_day: int = 25
    reposts_per_week: int = 3


@dataclass
class ClientCostLimitsConfig:
    daily_apify_budget_usd: float = 3.00
    monthly_apify_budget_usd: float = 60.00


@dataclass
class ClientKeywordsConfig:
    tier1_direct: list[str] = field(default_factory=list)
    tier2_lateral: list[str] = field(default_factory=list)
    tier3_platforms: list[str] = field(default_factory=list)


@dataclass
class ClientConfig:
    """All settings from the client YAML file."""

    client_id: str = ""
    display_name: str = ""
    niche: NicheConfig = field(default_factory=NicheConfig)
    keywords: ClientKeywordsConfig = field(default_factory=ClientKeywordsConfig)
    collection: ClientCollectionConfig = field(default_factory=ClientCollectionConfig)
    filter: ClientFilterConfig = field(default_factory=ClientFilterConfig)
    scoring: ClientScoringConfig = field(default_factory=ClientScoringConfig)
    action_limits: ClientActionLimitsConfig = field(default_factory=ClientActionLimitsConfig)
    influencer_watchlist: list[str] = field(default_factory=list)
    cost_limits: ClientCostLimitsConfig = field(default_factory=ClientCostLimitsConfig)

    # Env-derived aliases (backwards compat with v1.0 code)
    # These are set after merge
    niche_description: str = ""
    max_posts_per_keyword: int = 30
    seed_keywords: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    """
    Single merged config object used by every module.

    No module should read .env, YAML files, or os.environ directly.
    """

    # -- Client identification --
    client_id: str = ""
    client: ClientConfig = field(default_factory=ClientConfig)

    # -- Secrets (from .env) --
    apify_token: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    database_url: str = "sqlite:///./data/engagement.db"

    # -- Shared config (from config.yaml) --
    actors: ActorConfig = field(default_factory=ActorConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    # -- Client data sub-paths (derived) --
    raw_dir: str = ""
    filtered_dir: str = ""
    plans_dir: str = ""
    output_dir: str = ""
    exports_dir: str = ""
    errors_dir: str = ""

    # -- Runtime flags (CLI-driven, not persisted to YAML) --
    # When True, every external/paid call (Apify, LLM) must return a mocked
    # response from the same call site instead of hitting the real API.
    dry_run: bool = False


# ── Helper: recursive dict-to-dataclass ────────────────────────────────


def _dict_to_dataclass(dc_type, data: dict):
    """Convert a nested dict to a dataclass, recursively handling nested dataclasses."""
    if data is None:
        return dc_type()
    field_types = {f.name: f.type for f in dc_type.__dataclass_fields__.values()}
    kwargs = {}
    for key, value in data.items():
        if key in field_types:
            ft = field_types[key]
            # Handle list[str] and similar
            origin = getattr(ft, "__origin__", None)
            if origin is list and isinstance(value, list):
                kwargs[key] = value
            elif isinstance(value, dict) and hasattr(ft, "__dataclass_fields__"):
                kwargs[key] = _dict_to_dataclass(ft, value)
            elif isinstance(value, dict) and isinstance(ft, type) and hasattr(ft, "__dataclass_fields__"):
                kwargs[key] = _dict_to_dataclass(ft, value)
            else:
                kwargs[key] = value
    # Fill missing optional fields with defaults
    for f_name, f_field in dc_type.__dataclass_fields__.items():
        if f_name not in kwargs:
            if f_field.default is not dataclasses.MISSING:
                kwargs[f_name] = f_field.default
            elif f_field.default_factory is not dataclasses.MISSING:
                kwargs[f_name] = f_field.default_factory()
    return dc_type(**kwargs)




# ── Public API ─────────────────────────────────────────────────────────


def load_config(client_id_override: str = None, dry_run: bool = False) -> AppConfig:
    """
    1. Load .env (secrets)
    2. Load config.yaml (shared config)
    3. Determine active client: CLI override → config.yaml active_client
    4. Load clients/{client_id}.yaml
    5. Merge: client YAML values override config.yaml defaults
    6. Return single AppConfig object

    ``dry_run`` is a CLI-driven runtime flag (not a YAML setting) — when True,
    `collector/apify_client.py` and `content/llm_client.py` return mocked
    responses instead of making real paid calls.
    """
    # 1. Load .env
    load_dotenv()

    apify_token = os.environ.get("APIFY_API_TOKEN", "")
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    llm_base_url = os.environ.get("LLM_BASE_URL", "https://api.laozhang.ai/v1")
    # DB path defaults to client-aware; override via DATABASE_URL in .env
    database_url = os.environ.get("DATABASE_URL", "")

    # 2. Load config.yaml
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        with open(cfg_path) as f:
            cfg_yaml = yaml.safe_load(f) or {}
    else:
        cfg_yaml = {}

    # 3. Determine active client
    active_client = client_id_override or cfg_yaml.get("active_client", "Joinee")

    # 4. Build shared config dataclasses from YAML
    actors = _dict_to_dataclass(ActorConfig, cfg_yaml.get("actors", {}))
    llm = _dict_to_dataclass(LLMConfig, cfg_yaml.get("llm", {}))
    llm.api_key = llm_api_key
    llm.base_url = llm_base_url
    defaults = _dict_to_dataclass(DefaultsConfig, cfg_yaml.get("defaults", {}))
    paths = _dict_to_dataclass(PathsConfig, cfg_yaml.get("paths", {}))

    # 5. Load client YAML
    client_yaml_path = Path(paths.clients_dir) / f"{active_client}.yaml"
    if client_yaml_path.exists():
        with open(client_yaml_path) as f:
            client_data = yaml.safe_load(f) or {}
    else:
        client_data = {}

    client_obj = _dict_to_dataclass(ClientConfig, client_data)

    # Override client_id from filename (safety)
    client_obj.client_id = active_client

    # 6. Merge: client values override config defaults where client YAML has them
    #    Also set backwards-compat aliases on client_obj
    if not client_obj.niche_description:
        niche = client_obj.niche
        if isinstance(niche, dict):
            client_obj.niche_description = niche.get("product_description", "")
        elif hasattr(niche, "product_description"):
            client_obj.niche_description = niche.product_description
    if not client_obj.seed_keywords:
        # Build from tier1 + tier2
        kw = client_obj.keywords
        all_kw = list(kw.tier1_direct) + list(kw.tier2_lateral)
        client_obj.seed_keywords = all_kw
    # The client YAML expresses volume via collection.posts_per_keyword; honour
    # it as the source of truth for posts-per-keyword (the bare
    # max_posts_per_keyword field is a v1.0 alias with no YAML key of its own).
    if client_obj.collection.posts_per_keyword:
        client_obj.max_posts_per_keyword = client_obj.collection.posts_per_keyword
    elif client_obj.max_posts_per_keyword <= 0:
        client_obj.max_posts_per_keyword = client_obj.collection.posts_per_keyword

    # Build derived sub-paths
    client_data_dir = str(Path(paths.data_dir) / active_client)

    paths.client_data_dir = client_data_dir

    # Derive database URL if not explicitly set in .env
    if not database_url:
        db_path = Path(client_data_dir) / "engagement.db"
        database_url = f"sqlite:///{db_path.as_posix()}"

    raw_dir = str(Path(client_data_dir) / "raw")
    filtered_dir = str(Path(client_data_dir) / "filtered")
    plans_dir = str(Path(client_data_dir) / "plans")
    output_dir = str(Path(client_data_dir) / "output")
    exports_dir = str(Path(client_data_dir) / "exports")
    errors_dir = str(Path(client_data_dir) / "errors")

    # 7. Construct final AppConfig
    config = AppConfig(
        client_id=active_client,
        client=client_obj,
        apify_token=apify_token,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        database_url=database_url,
        actors=actors,
        llm=llm,
        defaults=defaults,
        paths=paths,
        raw_dir=raw_dir,
        filtered_dir=filtered_dir,
        plans_dir=plans_dir,
        output_dir=output_dir,
        exports_dir=exports_dir,
        errors_dir=errors_dir,
        dry_run=dry_run,
    )

    return config


def ensure_client_dirs(config: AppConfig):
    """Create data/{client_id}/ subdirectories if they don't exist. Silent if already exist."""
    subdirs = ["raw", "filtered", "plans", "output", "exports", "errors"]
    base = Path(config.paths.data_dir) / config.client_id
    base.mkdir(parents=True, exist_ok=True)
    for subdir in subdirs:
        (base / subdir).mkdir(parents=True, exist_ok=True)


def build_niche_embedding_text(niche: NicheConfig) -> str:
    """Dense concatenated text for semantic embedding."""
    parts = [
        niche.product_description,
        niche.primary_use_case,
        " ".join(niche.expanding_use_cases),
        " ".join(niche.target_audience),
        " ".join(niche.pain_vocabulary),
    ]
    return " ".join(p for p in parts if p)


def build_niche_prompt_context(niche: NicheConfig) -> str:
    """Structured multi-line string for injection into LLM system prompts."""
    lines = [
        f"Product description: {niche.product_description}",
        f"Primary use case: {niche.primary_use_case}",
        "Expanding use cases:",
    ]
    for uc in niche.expanding_use_cases:
        lines.append(f"  - {uc}")
    lines.append("Target audience:")
    for ta in niche.target_audience:
        lines.append(f"  - {ta}")
    lines.append("Pain vocabulary:")
    for pv in niche.pain_vocabulary:
        lines.append(f"  - {pv}")
    return "\n".join(lines)