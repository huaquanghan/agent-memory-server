# Configuration

The Redis Agent Memory Server can be configured via environment variables or YAML configuration files. All settings have sensible defaults for development, but you'll want to customize them for production.

## Configuration Methods

### Environment Variables
Setting names map directly to environment variables in UPPERCASE:
```bash
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=your-key-here
export GENERATION_MODEL=gpt-4o
```

### YAML Configuration File
Set `REDIS_MEMORY_CONFIG` to point to a YAML file:
```bash
export REDIS_MEMORY_CONFIG=config.yaml
```

Example `config.yaml`:
```yaml
redis_url: redis://localhost:6379
generation_model: gpt-4o
embedding_model: text-embedding-3-small
enable_topic_extraction: true
log_level: INFO
```

**Note**: Environment variables override YAML file settings.

## Core Settings

### Redis Connection
```bash
REDIS_URL=redis://localhost:6379  # Redis connection string
```

### AI Model Configuration
```bash
# Generation models for LLM tasks
GENERATION_MODEL=gpt-4o              # Primary model (default: gpt-4o)
SLOW_MODEL=gpt-4o                    # Complex tasks (default: gpt-4o)
FAST_MODEL=gpt-4o-mini               # Quick tasks (default: gpt-4o-mini)

# Embedding model for vector search
EMBEDDING_MODEL=text-embedding-3-small  # OpenAI embeddings (default)

# API Keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Optional: Custom API endpoints
OPENAI_API_BASE=https://api.openai.com/v1
ANTHROPIC_API_BASE=https://api.anthropic.com
```

### Server Ports
```bash
PORT=8000          # REST API port (default: 8000)
MCP_PORT=9000      # MCP server port (default: 9000)
```

## Memory System Configuration

### Long-Term Memory
```bash
LONG_TERM_MEMORY=true                    # Enable persistent memory (default: true)
ENABLE_DISCRETE_MEMORY_EXTRACTION=true  # Extract structured memories from conversations (default: true)
INDEX_ALL_MESSAGES_IN_LONG_TERM_MEMORY=false  # Index every message (default: false)
```

### Vector Store Configuration
```bash
# Vector store factory (advanced)
VECTORSTORE_FACTORY=agent_memory_server.vectorstore_factory.create_redis_vectorstore

# RedisVL Settings (used by default Redis factory)
REDISVL_INDEX_NAME=memory_records        # Index name (default: memory_records)
REDISVL_DISTANCE_METRIC=COSINE           # Distance metric (default: COSINE)
REDISVL_VECTOR_DIMENSIONS=1536           # Vector dimensions (default: 1536)
REDISVL_INDEX_PREFIX=memory_idx          # Index prefix (default: memory_idx)
REDISVL_INDEXING_ALGORITHM=HNSW          # Indexing algorithm (default: HNSW)
```

### Working Memory
```bash
SUMMARIZATION_THRESHOLD=0.7  # Fraction of context window that triggers summarization (default: 0.7)
```

## AI Features Configuration

### Topic Modeling
```bash
ENABLE_TOPIC_EXTRACTION=true     # Extract topics from memories (default: true)
TOPIC_MODEL_SOURCE=LLM           # Options: LLM, BERTopic (default: LLM)
TOPIC_MODEL=gpt-4o-mini          # Model for topic extraction (default: gpt-4o-mini)
TOP_K_TOPICS=3                   # Maximum topics per memory (default: 3)
```

### Entity Recognition
```bash
ENABLE_NER=true                  # Extract entities from text (default: true)
NER_MODEL=dbmdz/bert-large-cased-finetuned-conll03-english  # NER model (default)
```

### Query Optimization
```bash
MIN_OPTIMIZED_QUERY_LENGTH=2     # Minimum query length to optimize (default: 2)

# Custom query optimization prompt template
QUERY_OPTIMIZATION_PROMPT_TEMPLATE="Transform this query for semantic search..."
```

## Memory Lifecycle

### Memory Management Configuration
```bash
# Forgetting settings
FORGETTING_ENABLED=false          # Enable automatic forgetting (default: false)
FORGETTING_EVERY_MINUTES=60       # Run forgetting every N minutes (default: 60)
FORGETTING_MAX_AGE_DAYS=30        # Delete memories older than N days
FORGETTING_MAX_INACTIVE_DAYS=7    # Delete memories inactive for N days
FORGETTING_BUDGET_KEEP_TOP_N=1000 # Keep only top N most recent memories

# Compaction settings
COMPACTION_EVERY_MINUTES=10       # Run memory compaction every N minutes (default: 10)
```

## Background Tasks

### Docket Configuration
```bash
USE_DOCKET=true           # Enable background task processing (default: true)
DOCKET_NAME=memory-server # Docket instance name (default: memory-server)
```

## Application Settings

### Logging
```bash
LOG_LEVEL=INFO            # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
```

### MCP Defaults
```bash
DEFAULT_MCP_USER_ID=default-user    # Default user ID for MCP requests
DEFAULT_MCP_NAMESPACE=default       # Default namespace for MCP requests
```

## Running the Background Task Worker

The Redis Memory Server uses Docket for background task management. You can run a worker instance like this:

```bash
uv run agent-memory task-worker
```

You can customize the concurrency and redelivery timeout:

```bash
uv run agent-memory task-worker --concurrency 5 --redelivery-timeout 60
```

## Supported Models

### Generation Models (OpenAI)
- `gpt-4o` - Latest GPT-4 Optimized (recommended)
- `gpt-4o-mini` - Faster, smaller GPT-4 (good for fast_model)
- `gpt-4` - Previous GPT-4 version
- `gpt-3.5-turbo` - Older, faster model
- `o1` - OpenAI o1 reasoning model
- `o1-mini` - Smaller o1 model
- `o3-mini` - OpenAI o3 model

### Generation Models (Anthropic)
- `claude-3-7-sonnet-latest` - Latest Claude 3.7 Sonnet (recommended)
- `claude-3-5-sonnet-latest` - Claude 3.5 Sonnet
- `claude-3-5-haiku-latest` - Fast Claude 3.5 Haiku
- `claude-3-opus-latest` - Most capable Claude model
- Version-specific models also supported (e.g., `claude-3-5-sonnet-20241022`)

### Embedding Models (OpenAI only)
- `text-embedding-3-small` - 1536 dimensions (recommended)
- `text-embedding-3-large` - 3072 dimensions (higher accuracy)
- `text-embedding-ada-002` - Legacy model (1536 dimensions)

## Configuration Examples

### Development Setup
```yaml
# config-dev.yaml
redis_url: redis://localhost:6379
generation_model: gpt-4o-mini  # Faster for development
embedding_model: text-embedding-3-small
log_level: DEBUG
disable_auth: true
enable_topic_extraction: false  # Skip AI features for faster startup
enable_ner: false
```

### Production Setup
```yaml
# config-prod.yaml
redis_url: redis://prod-redis:6379
generation_model: gpt-4o
embedding_model: text-embedding-3-large
log_level: INFO
auth_mode: oauth2
oauth2_issuer_url: https://your-auth.com
oauth2_audience: https://your-api.com
enable_topic_extraction: true
enable_ner: true
forgetting_enabled: true
forgetting_max_age_days: 90
compaction_every_minutes: 15
```

### High-Performance Setup
```yaml
# config-performance.yaml
redis_url: redis://redis-cluster:6379
fast_model: gpt-4o-mini
slow_model: gpt-4o
redisvl_indexing_algorithm: HNSW
redisvl_vector_dimensions: 1536
use_docket: true
summarization_threshold: 0.8  # Less frequent summarization
```

## Running Migrations

When the data model changes, we add a migration in `migrations.py`. You can run
these to make sure your schema is up to date, like so:

```bash
uv run agent-memory migrate-memories
```

## Authentication Configuration

The Redis Memory Server supports multiple authentication modes configured via environment variables:

### Authentication Mode Settings

```bash
# Primary authentication mode setting
AUTH_MODE=disabled  # Options: disabled, token, oauth2 (default: disabled)

# Legacy setting (for backward compatibility)
DISABLE_AUTH=true   # Set to true to bypass all authentication

# Alternative token auth setting
TOKEN_AUTH_ENABLED=true  # Alternative way to enable token authentication
```

### OAuth2/JWT Settings

Required when `AUTH_MODE=oauth2`:

```bash
OAUTH2_ISSUER_URL=https://your-auth-provider.com
OAUTH2_AUDIENCE=your-api-audience
OAUTH2_JWKS_URL=https://your-auth-provider.com/.well-known/jwks.json  # Optional
OAUTH2_ALGORITHMS=["RS256"]  # Supported algorithms (default: ["RS256"])
```

### Token Authentication

When using `AUTH_MODE=token`:

- Tokens are managed via CLI commands (`agent-memory token`)
- No additional environment variables required
- Tokens are stored securely in Redis with bcrypt hashing
- Optional expiration dates supported

### Examples

**Development (No Authentication):**
```bash
export AUTH_MODE=disabled
# OR
export DISABLE_AUTH=true
```

**Production with Token Authentication:**
```bash
export AUTH_MODE=token
```

**Production with OAuth2:**
```bash
export AUTH_MODE=oauth2
export OAUTH2_ISSUER_URL=https://your-domain.auth0.com/
export OAUTH2_AUDIENCE=https://your-api.com
```

For detailed authentication setup and usage, see the [Authentication Documentation](authentication.md).
