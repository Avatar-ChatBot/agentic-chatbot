# OpenRouter Migration Plan: From Together AI to OpenRouter with Qwen3 2335B

## Executive Summary

This document outlines the research findings and implementation plan for migrating the agentic chatbot from Together AI (`langchain-together`) to OpenRouter, specifically to use the latest Qwen3 2335B model (`qwen/qwen3-235b-a22b`). The migration leverages OpenRouter's OpenAI-compatible API, allowing seamless integration with existing LangChain infrastructure.

### Key Changes Overview

**Core Application:**
- Remove `langchain-together==0.3.0` dependency
- Replace `ChatTogether` with `ChatOpenAI` configured for OpenRouter
- Update model from `Qwen/Qwen2.5-72B-Instruct-Turbo` to `qwen/qwen3-235b-a22b`
- Add `OPENROUTER_API_KEY` environment variable

**Deployment Configuration:**
- Update `config.py` validation to require `OPENROUTER_API_KEY`
- Update `validate.py` to check for `OPENROUTER_API_KEY`
- Update `DEPLOYMENT_GUIDE.md` environment variables section
- Update `DEPLOYMENT_SUMMARY.md` references
- Update `.cursor/` documentation files (if present)

**Files Modified:** 9 files (3 core + 6 deployment config)
**Files Unchanged:** 6 files (no changes needed)

---

## 1. Current State Analysis

### 1.1 Current Dependencies (from `requirements.txt`)

```
langchain==0.3.7
langchain-community==0.3.5
langchain-core==0.3.60
langchain-openai==0.3.17
langchain-together==0.3.0  # ⚠️ TO BE REMOVED
```

### 1.2 Current LLM Configuration

**File: `agents/models.py`**
- **Current Provider:** Together AI
- **Current Model:** `Qwen/Qwen2.5-72B-Instruct-Turbo`
- **Current Implementation:**
  ```python
  from langchain_together import ChatTogether
  llm = ChatTogether(model="Qwen/Qwen2.5-72B-Instruct-Turbo", temperature=0)
  ```

### 1.3 Current Usage Points

1. **`agents/models.py`** - Main LLM initialization
2. **`agents/rag.py`** - RAG agent uses `llm` from `agents.models`
3. **`agents/sql.py`** - SQL agent uses `llm` from `agents.models` (line 14)
4. **`config.py`** - Contains `TOGETHER_API_KEY` configuration

---

## 2. Research Findings

### 2.1 OpenRouter Compatibility with LangChain

**Key Finding:** OpenRouter provides an OpenAI-compatible API, which means:
- ✅ **Compatible with `langchain-openai`** (already in dependencies)
- ✅ **No additional package needed** - can use existing `langchain-openai==0.3.17`
- ✅ **Works with LangChain 0.3.x** - fully compatible with current versions
- ✅ **Seamless integration** - minimal code changes required

### 2.2 Integration Approach

Two approaches are available:

#### Approach 1: Direct `ChatOpenAI` Configuration (Recommended)
Use `langchain-openai.ChatOpenAI` with OpenRouter's base URL:
- ✅ Simpler implementation
- ✅ Uses existing package
- ✅ Less code to maintain

#### Approach 2: Custom `ChatOpenRouter` Class
Create a subclass of `ChatOpenAI`:
- More explicit naming
- Slightly more code

**Recommendation:** Use Approach 1 for simplicity.

### 2.3 Model Identifier

**Target Model:** Qwen3 2335B (identifier: qwen/qwen3-235b-a22b)
Source: https://openrouter.ai/qwen/qwen3-235b-a22b


### 2.4 API Configuration

**OpenRouter API Endpoint:** `https://openrouter.ai/api/v1`

**Required Headers (Optional but recommended):**
- `HTTP-Referer`: Your site URL (for analytics)
- `X-Title`: Your application name (for analytics)

**Authentication:** Uses `OPENROUTER_API_KEY` environment variable

---

## 3. Compatibility Matrix

| Component | Current Version | OpenRouter Compatible | Notes |
|-----------|----------------|----------------------|-------|
| `langchain` | 0.3.7 | ✅ Yes | No change needed |
| `langchain-openai` | 0.3.17 | ✅ Yes | Already compatible |
| `langchain-core` | 0.3.60 | ✅ Yes | No change needed |
| `langchain-community` | 0.3.5 | ✅ Yes | No change needed |
| `langchain-together` | 0.3.0 | ❌ Remove | No longer needed |

**Conclusion:** All current LangChain versions are compatible with OpenRouter. Only need to remove `langchain-together`.

---

## 4. Implementation Plan

### Phase 1: Environment Configuration

#### 4.1.1 Update `config.py`

**File:** `config.py`

**Changes:**
1. Add `OPENROUTER_API_KEY` configuration
2. Remove or deprecate `TOGETHER_API_KEY` (optional - keep for backward compatibility during transition)
3. Update validation method

**Code Changes:**

```python
# In Config class, update LLM Providers section:
# LLM Providers
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")  # Keep for now, mark as deprecated
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # NEW
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Update validate() method:
required = [
    ("API_KEY", cls.API_KEY),
    ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
    ("OPENROUTER_API_KEY", cls.OPENROUTER_API_KEY),  # NEW - replace TOGETHER_API_KEY
    ("PINECONE_API_KEY", cls.PINECONE_API_KEY),
]
```

**Location:** Lines 18-20, 66-71

---

### Phase 2: Update Dependencies

#### 4.2.1 Update `requirements.txt`

**File:** `requirements.txt`

**Changes:**
1. Remove `langchain-together==0.3.0`
2. Keep all other dependencies unchanged

**Code Changes:**

```diff
langchain==0.3.7
langchain-community==0.3.5
langchain-core==0.3.60
langchain-openai==0.3.17
langchain-pinecone==0.2.0
langgraph==0.2.48
langgraph-checkpoint==2.0.4
langgraph-sdk==0.1.36
langsmith==0.1.145
- langchain-together==0.3.0
```

**Location:** Line 15

---

### Phase 3: Update LLM Initialization

#### 4.3.1 Update `agents/models.py`

**File:** `agents/models.py`

**Changes:**
1. Remove `from langchain_together import ChatTogether`
2. Update import to use `ChatOpenAI` from `langchain_openai` (already imported)
3. Replace `ChatTogether` initialization with `ChatOpenAI` configured for OpenRouter
4. Update model name to Qwen3 2335B (exact identifier TBD)

**Code Changes:**

```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
# Remove: from langchain_together import ChatTogether
import os

load_dotenv()

# ... existing commented code ...

# NEW: OpenRouter LLM configuration
llm = ChatOpenAI(
    model="qwen/qwen3-235b-a22b",  # Verified model identifier
    temperature=0,
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": os.getenv("SITE_URL", "https://your-site.com"),  # Optional
        "X-Title": os.getenv("APP_NAME", "ITB Chatbot"),  # Optional
    },
    timeout=60,  # Match Config.LLM_TIMEOUT if needed
)

# Keep existing fallback LLM
llm_4o_mini = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# ... rest of the file unchanged ...
```

**Location:** Lines 1-20

**Alternative Approach (Custom Class):**

If preferred, create a custom class:

```python
from langchain_openai import ChatOpenAI
from typing import Optional
import os

class ChatOpenRouter(ChatOpenAI):
    """Custom ChatOpenAI subclass configured for OpenRouter"""
    def __init__(
        self,
        model: str,
        temperature: float = 0,
        **kwargs
    ):
        super().__init__(
            model=model,
            temperature=temperature,
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": os.getenv("SITE_URL", "https://your-site.com"),
                "X-Title": os.getenv("APP_NAME", "ITB Chatbot"),
            },
            **kwargs
        )

# Then use:
llm = ChatOpenRouter(model="qwen/qwen3-235b-a22b", temperature=0)
```

---

### Phase 4: Verify No Breaking Changes

#### 4.4.1 Check Usage in `agents/rag.py`

**File:** `agents/rag.py`

**Status:** ✅ **No changes needed**
- Already imports `llm` from `agents.models`
- Will automatically use new OpenRouter LLM

**Location:** Line 7

#### 4.4.2 Check Usage in `agents/sql.py`

**File:** `agents/sql.py`

**Status:** ✅ **No changes needed**
- Already imports `llm` from `agents.models`
- Will automatically use new OpenRouter LLM

**Location:** Line 6, 14

---

### Phase 5: Environment Variables

#### 5.1 Required Environment Variables

**Add to `.env` file:**

```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: For OpenRouter analytics headers
SITE_URL=https://your-site.com
APP_NAME=ITB Chatbot
```

**Remove (optional - can keep during transition):**
```bash
# TOGETHER_API_KEY=...  # Can be removed after migration
```

#### 5.2 Update Documentation

**Files to update:**
- `DEPLOYMENT_GUIDE.md` (if exists)
- `README.md` (if exists)
- Any environment variable documentation

**Changes:**
- Replace `TOGETHER_API_KEY` references with `OPENROUTER_API_KEY`
- Update LLM provider information
- Update model name references

---

### Phase 6: Update Deployment Configuration

#### 6.1 Update `DEPLOYMENT_GUIDE.md`

**File:** `DEPLOYMENT_GUIDE.md`

**Changes:**
1. Update environment variables section to replace `TOGETHER_API_KEY` with `OPENROUTER_API_KEY`
2. Update LLM provider description
3. Update any references to Together AI

**Code Changes:**

```markdown
### Environment Variables

All configuration is managed through environment variables in `.env`:

**Required:**
- `API_KEY` - API authentication key
- `OPENAI_API_KEY` - OpenAI API key (embeddings)
- `OPENROUTER_API_KEY` - OpenRouter API key (LLM)  # CHANGED from TOGETHER_API_KEY
- `PINECONE_API_KEY` - Pinecone API key (vector DB)
```

**Location:** Line 163

**Additional Updates:**
- Update any mentions of "Together AI" to "OpenRouter"
- Update model name references from "Qwen/Qwen2.5-72B-Instruct-Turbo" to "qwen/qwen3-235b-a22b"
- Update provider setup instructions if present

---

#### 6.2 Update `DEPLOYMENT_SUMMARY.md`

**File:** `DEPLOYMENT_SUMMARY.md`

**Changes:**
1. Update any references to Together AI
2. Update LLM provider information
3. Update model name references

**Code Changes:**

Search and replace:
- `TOGETHER_API_KEY` → `OPENROUTER_API_KEY`
- `Together AI` → `OpenRouter`
- `Qwen/Qwen2.5-72B-Instruct-Turbo` → `qwen/qwen3-235b-a22b`

**Location:** Throughout the file (if present)

---

#### 6.3 Update `validate.py`

**File:** `validate.py`

**Changes:**
1. Update validation to check for `OPENROUTER_API_KEY` instead of `TOGETHER_API_KEY`
2. Update required environment variables list

**Code Changes:**

```python
# In validate_config() function, update required list:
required = [
    ("API_KEY", Config.API_KEY),
    ("OPENAI_API_KEY", Config.OPENAI_API_KEY),
    ("OPENROUTER_API_KEY", Config.OPENROUTER_API_KEY),  # CHANGED from TOGETHER_API_KEY
    ("PINECONE_API_KEY", Config.PINECONE_API_KEY),
]
```

**Location:** Lines 46-51

---

#### 6.4 Update `docker-compose.yml`

**File:** `docker-compose.yml`

**Status:** ✅ **No changes needed**
- Uses `.env` file for environment variables
- Will automatically pick up `OPENROUTER_API_KEY` from `.env`
- No hardcoded references to `TOGETHER_API_KEY`

**Note:** Ensure `.env` file is updated with `OPENROUTER_API_KEY` before deployment

---

#### 6.5 Update `Dockerfile`

**File:** `Dockerfile`

**Status:** ✅ **No changes needed**
- No environment variable references
- No provider-specific code

---

#### 6.6 Update `test_deployment.sh`

**File:** `test_deployment.sh`

**Status:** ✅ **No changes needed**
- No references to `TOGETHER_API_KEY`
- Tests are provider-agnostic

---

#### 6.7 Update `.cursor/plans/deployment-plan.md` (if exists)

**File:** `.cursor/plans/deployment-plan.md`

**Changes:**
1. Update environment variable examples
2. Update LLM provider setup instructions
3. Replace Together AI references with OpenRouter

**Code Changes:**

```markdown
# In environment setup section:
export OPENROUTER_API_KEY="your-openrouter-api-key"  # CHANGED from TOGETHER_API_KEY

# In .env.example section:
OPENROUTER_API_KEY=your_openrouter_api_key_here  # CHANGED from TOGETHER_API_KEY
```

**Location:** Throughout the file (if present)

---

#### 6.8 Update `.cursor/analysis/deployment-analysis.md` (if exists)

**File:** `.cursor/analysis/deployment-analysis.md`

**Changes:**
1. Update environment variables analysis section
2. Replace Together AI references with OpenRouter
3. Update cost and usage information

**Code Changes:**

```markdown
#### 3. **OPENROUTER_API_KEY** (OpenRouter Services)  # CHANGED from TOGETHER_API_KEY
- **Purpose:** Primary LLM (qwen/qwen3-235b-a22b)
- **Format:** String (OpenRouter API key)
- **Security Level:** CRITICAL
- **Usage:** `agents/models.py` line 19
- **Cost Impact:** HIGH (primary inference engine)
- **Recommendation:**
  - Set up billing alerts
  - Monitor token usage
  - Consider request queuing for cost control
```

**Location:** Lines 139-148 (if present)

---

#### 6.9 Update `.cursor/rules/general.md` (if exists)

**File:** `.cursor/rules/general.md`

**Changes:**
1. Update environment variables section
2. Replace `TOGETHER_API_KEY` with `OPENROUTER_API_KEY`

**Code Changes:**

```markdown
## Environment Variables Required

```bash
# API Security
API_KEY=your_api_key_here

# LLM & Embeddings
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_openrouter_key  # CHANGED from TOGETHER_API_KEY

# Vector Database
PINECONE_API_KEY=your_pinecone_key
...
```

**Location:** Lines 103-125 (if present)

---

## 5. Code Changes Summary

### Files to Modify

#### Core Application Files

1. ✅ **`requirements.txt`**
   - Remove `langchain-together==0.3.0`

2. ✅ **`config.py`**
   - Add `OPENROUTER_API_KEY` to Config class
   - Update `validate()` method to require `OPENROUTER_API_KEY` instead of `TOGETHER_API_KEY`

3. ✅ **`agents/models.py`**
   - Remove `from langchain_together import ChatTogether`
   - Replace `ChatTogether` initialization with `ChatOpenAI` configured for OpenRouter
   - Update model name to `qwen/qwen3-235b-a22b`

#### Deployment Configuration Files

4. ✅ **`validate.py`**
   - Update `validate_config()` function
   - Replace `TOGETHER_API_KEY` with `OPENROUTER_API_KEY` in required variables list

5. ✅ **`DEPLOYMENT_GUIDE.md`**
   - Update environment variables section
   - Replace `TOGETHER_API_KEY` with `OPENROUTER_API_KEY`
   - Update LLM provider description
   - Update model name references

6. ✅ **`DEPLOYMENT_SUMMARY.md`**
   - Update any references to Together AI
   - Update LLM provider information
   - Update model name references

7. ✅ **`.cursor/plans/deployment-plan.md`** (if exists)
   - Update environment variable examples
   - Update LLM provider setup instructions
   - Replace Together AI references with OpenRouter

8. ✅ **`.cursor/analysis/deployment-analysis.md`** (if exists)
   - Update environment variables analysis section
   - Replace Together AI references with OpenRouter
   - Update cost and usage information

9. ✅ **`.cursor/rules/general.md`** (if exists)
   - Update environment variables section
   - Replace `TOGETHER_API_KEY` with `OPENROUTER_API_KEY`

### Files That Don't Need Changes

- ✅ `agents/rag.py` - Uses `llm` from `agents.models` (automatic)
- ✅ `agents/sql.py` - Uses `llm` from `agents.models` (automatic)
- ✅ `app.py` - No direct LLM usage
- ✅ `docker-compose.yml` - Uses `.env` file (no hardcoded references)
- ✅ `Dockerfile` - No environment variable references
- ✅ `test_deployment.sh` - No provider-specific references
- ✅ All other files - No LLM dependencies

---

## 6. Testing Checklist

### 6.1 Pre-Implementation Verification

- [ ] Verify exact Qwen3 2335B model identifier on OpenRouter
- [ ] Obtain OpenRouter API key
- [ ] Test OpenRouter API key with a simple curl request

### 6.2 Post-Implementation Testing

- [ ] Test RAG agent with new LLM (`/v1/chat` endpoint)
- [ ] Test audio processing with new LLM (`/v1/audio` endpoint)
- [ ] Test SQL agent (if used)
- [ ] Verify response quality matches or exceeds previous model
- [ ] Check error handling for invalid API key
- [ ] Verify timeout handling
- [ ] Test with various conversation threads
- [ ] Monitor API costs and rate limits

### 6.3 Rollback Plan

If issues occur:
1. Revert `agents/models.py` to use `ChatTogether`
2. Re-add `langchain-together==0.3.0` to `requirements.txt`
3. Restore `TOGETHER_API_KEY` in environment

---

## 7. Implementation Steps (Sequential)

### Step 1: Research & Verification
- [ ] Verify exact Qwen3 2335B model name on OpenRouter
- [ ] Test OpenRouter API key access
- [ ] Review OpenRouter pricing and rate limits

### Step 2: Update Dependencies
- [ ] Remove `langchain-together==0.3.0` from `requirements.txt`
- [ ] Run `pip install -r requirements.txt` to update environment

### Step 3: Update Configuration
- [ ] Add `OPENROUTER_API_KEY` to `config.py`
- [ ] Update `validate()` method in `config.py`
- [ ] Add `OPENROUTER_API_KEY` to `.env` file

### Step 4: Update LLM Initialization
- [ ] Remove `ChatTogether` import from `agents/models.py`
- [ ] Replace LLM initialization with OpenRouter configuration
- [ ] Update model name to verified Qwen3 2335B identifier

### Step 5: Testing
- [ ] Run unit tests (if available)
- [ ] Test `/v1/chat` endpoint
- [ ] Test `/v1/audio` endpoint
- [ ] Verify response quality

### Step 6: Update Deployment Configuration
- [ ] Update `validate.py` to check for `OPENROUTER_API_KEY`
- [ ] Update `DEPLOYMENT_GUIDE.md` environment variables section
- [ ] Update `DEPLOYMENT_SUMMARY.md` references
- [ ] Update `.cursor/plans/deployment-plan.md` (if exists)
- [ ] Update `.cursor/analysis/deployment-analysis.md` (if exists)
- [ ] Update `.cursor/rules/general.md` (if exists)

### Step 7: Testing
- [ ] Run `python validate.py` to verify configuration
- [ ] Run unit tests (if available)
- [ ] Test `/v1/chat` endpoint
- [ ] Test `/v1/audio` endpoint
- [ ] Verify response quality
- [ ] Test deployment with `docker-compose up`

### Step 8: Documentation
- [ ] Update environment variable documentation
- [ ] Update deployment guides
- [ ] Update README if needed
- [ ] Verify all documentation references are updated

### Step 9: Cleanup (Optional)
- [ ] Remove `TOGETHER_API_KEY` from `config.py` (after successful migration)
- [ ] Remove `TOGETHER_API_KEY` from `.env` file
- [ ] Remove any remaining Together AI references from documentation

---

## 8. Risk Assessment

### Low Risk ✅
- OpenRouter uses OpenAI-compatible API
- LangChain versions are compatible
- Minimal code changes required
- Easy rollback path

### Medium Risk ⚠️
- Model identifier verification needed
- Response format differences (should be minimal)
- Cost implications (verify pricing)

### Mitigation
- Test in development environment first
- Keep Together AI configuration as backup
- Monitor API usage and costs
- Gradual rollout if possible

---

## 9. Additional Considerations

### 9.1 Model Availability
- Verify Qwen3 2335B is available on OpenRouter
- Check if model requires special access or pricing tier
- Verify model supports required features (streaming, tool use, etc.)

### 9.2 Cost Analysis
- Compare OpenRouter pricing vs Together AI
- Monitor token usage
- Set up billing alerts

### 9.3 Performance
- Monitor response times
- Compare latency with previous setup
- Adjust timeout settings if needed

### 9.4 Headers Configuration
The optional headers (`HTTP-Referer`, `X-Title`) are recommended for:
- Analytics tracking
- Better support from OpenRouter
- Usage monitoring

Consider adding these to `config.py`:
```python
SITE_URL = os.getenv("SITE_URL", "https://your-site.com")
APP_NAME = os.getenv("APP_NAME", "ITB Chatbot")
```

---

## 10. References

- OpenRouter Documentation: https://openrouter.ai/docs
- OpenRouter LangChain Guide: https://openrouter.ai/docs/guides/community/lang-chain
- OpenRouter Models List: https://openrouter.ai/models
- LangChain OpenAI Integration: https://python.langchain.com/docs/integrations/chat/openai

---

## 11. Notes

### Model Name Verification
**✅ VERIFIED:** Model identifier confirmed:
- **Model:** `qwen/qwen3-235b-a22b`
- **Source:** https://openrouter.ai/qwen/qwen3-235b-a22b

### Alternative: API Verification
```bash
curl https://openrouter.ai/api/v1/models | jq '.data[] | select(.id | contains("qwen"))'
```

---

## 12. Estimated Implementation Time

- **Research & Verification:** 30 minutes
- **Core Code Changes:** 15 minutes
- **Deployment Config Updates:** 20 minutes
- **Testing:** 30-60 minutes
- **Documentation:** 20 minutes
- **Total:** ~2-2.5 hours

---

**Document Created:** Research Phase Complete
**Next Step:** Verify model identifier and proceed with implementation

