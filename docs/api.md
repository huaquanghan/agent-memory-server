# REST API Endpoints

The following endpoints are available:

- **GET /v1/health**
  A simple health check endpoint returning the current server time.
  Example Response:

  ```json
  { "now": 1616173200 }
  ```

- **GET /v1/working-memory/**
  Retrieves a paginated list of session IDs.
  _Query Parameters:_

  - `limit` (int): Number of sessions per page (default: 10)
  - `offset` (int): Number of sessions to skip (default: 0)
  - `namespace` (string, optional): Filter sessions by namespace.

- **GET /v1/working-memory/{session_id}**
  Retrieves working memory for a session, including messages, structured memories,
  context, and metadata.
  _Query Parameters:_

  - `namespace` (string, optional): The namespace to use for the session
  - `model_name` (string, optional): The client's LLM model name to determine appropriate context window size
  - `context_window_max` (int, optional): Direct specification of max context window tokens (overrides model_name)

- **PUT /v1/working-memory/{session_id}**
  Sets working memory for a session, replacing any existing memory.
  Automatically summarizes conversations that exceed the token limit.
  _Request Body Example:_

  ```json
  {
    "messages": [
      { "role": "user", "content": "Hello" },
      { "role": "assistant", "content": "Hi there" }
    ],
    "memories": [
      {
        "id": "mem-123",
        "text": "User prefers direct communication",
        "memory_type": "semantic"
      }
    ],
    "context": "Previous conversation summary...",
    "session_id": "session-123",
    "namespace": "default"
  }
  ```

- **DELETE /v1/working-memory/{session_id}**
  Deletes all working memory (messages, context, structured memories, metadata) for a session.

- **POST /v1/long-term-memory/**
  Creates long-term memories directly, bypassing working memory.
  _Request Body Example:_

  ```json
  {
    "memories": [
      {
        "id": "mem-456",
        "text": "User is interested in AI and machine learning",
        "memory_type": "semantic",
        "session_id": "session-123",
        "namespace": "default"
      }
    ]
  }
  ```

- **POST /v1/long-term-memory/search**
  Performs vector search on long-term memories with advanced filtering options.
  _Request Body Example:_

  ```json
  {
    "text": "Search query text",
    "limit": 10,
    "offset": 0,
    "session_id": { "eq": "session-123" },
    "namespace": { "eq": "default" },
    "topics": { "any": ["AI", "Machine Learning"] },
    "entities": { "all": ["OpenAI", "Claude"] },
    "created_at": { "gte": 1672527600, "lte": 1704063599 },
    "last_accessed": { "gt": 1704063600 },
    "user_id": { "eq": "user-456" }
  }
  ```

- **POST /v1/memory/prompt**
  Generates prompts enriched with relevant memory context from both working
  memory and long-term memory. Useful for retrieving context before answering questions.
  _Request Body Example:_

  ```json
  {
    "query": "What did we discuss about AI?",
    "session": {
      "session_id": "session-123",
      "namespace": "default",
      "model_name": "gpt-4o",
      "context_window_max": 4000
    },
    "long_term_search": {
      "text": "AI discussion",
      "limit": 5,
      "namespace": { "eq": "default" }
    }
  }
  ```

## Filter Options

_Filter options for search endpoints:_

- Tag filters (session_id, namespace, topics, entities, user_id):

  - `eq`: Equals this value
  - `ne`: Not equals this value
  - `any`: Contains any of these values
  - `all`: Contains all of these values

- Numeric filters (created_at, last_accessed):
  - `gt`: Greater than
  - `lt`: Less than
  - `gte`: Greater than or equal
  - `lte`: Less than or equal
  - `eq`: Equals
  - `ne`: Not equals
  - `between`: Between two values
