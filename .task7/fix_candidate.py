from pathlib import Path

root = Path.cwd()
provider = root / 'components/worker-lab/worker_lab/provider_qualification.py'
text = provider.read_text(encoding='utf-8')
text = text.replace('@dataclass(frozen=True)\n\n\nHttpJson =', 'HttpJson =')
provider.write_text(text, encoding='utf-8')

integration = root / 'components/worker-lab/worker_lab/integration_v3.py'
text = integration.read_text(encoding='utf-8')
text = text.replace('"openai_api_key", "codex_api_key", "github_token", "gh_token",', '"openai_api_key", "provider_api_key", "github_token", "gh_token",')
integration.write_text(text, encoding='utf-8')
