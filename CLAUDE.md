# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Backend

```bash
cd backend

# Create and activate virtual environment (first time)
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
venv\Scripts\activate.bat    # Windows CMD

# Install dependencies
pip install -r requirements.txt

# Optional: Install Marker PDF converter (high-quality, requires 5GB+ VRAM)
pip install marker-pdf>=0.2.6

# Set required environment variable (PowerShell)
$env:DASHSCOPE_API_KEY="your-api-key-here"

# Optional: Force CPU mode (set before starting server)
$env:PAPERREADER_DEVICE="cpu"

# Start development server
python -m app.main
# or with auto-reload:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Run tests
pytest                                          # all tests
pytest tests/test_pdf_processor.py -v          # specific file
pytest --cov=app --cov-report=html             # coverage report

# Verify device detection (GPU support)
python -c "from app.core.pdf_processor import detect_device; print(detect_device())"
```

### Frontend

```bash
cd frontend

# Install dependencies (first time)
npm install

# Start development server
npm run dev

# Type checking
npx tsc --noEmit

# Build production version
npm run build

# Preview production build
npm run preview
```

### Service URLs
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/v1/health

---

## Architecture Overview

### System Architecture

```
Frontend (React + Vite)
    ↓ HTTP/JSON
API Gateway (FastAPI)
    ↓
Business Logic (Core Services)
    ↓
File System Storage
```

### Document Processing Pipeline (Key Multi-File Pattern)

**The complete flow requires understanding interactions across multiple files:**

1. **Upload** (`app/api/v1/documents.py`):
   - User uploads PDF → `POST /api/v1/documents/upload`
   - **Optional**: `converter` parameter (`pix2text` or `marker`)
   - File validated, UUID generated as `doc_id`
   - Saved to `data/uploads/{doc_id}/original.pdf`
   - Background task added to `BackgroundTasks`

2. **Background Processing** (`app/core/document_processor.py`):
   - `process_document_background()` runs asynchronously
   - Passes `converter` parameter to `PDFProcessor`

3. **PDF Processing** (`app/core/pdf_processor.py`):
   - **PDFProcessor Facade**: Dynamically loads converter based on parameter
   - **Lazy Loading**: Converter model loaded via `@property` on first access
   - **Strategy Selection**: Pix2Text (fast) or Marker (high-quality)
   - **OCR Recognition**: Converter's `convert_to_markdown()` → Markdown text
   - **Image Extraction**: PyMuPDF extracts images → saved to `data/processed/images/{doc_id}/`
   - **Graceful Degradation**: If Marker unavailable, auto-fallback to Pix2Text

4. **State Tracking** (File System as State Store):
   - Success: `data/processed/markdown/{doc_id}.md` created
   - Failure: `data/processed/markdown/{doc_id}.error` created with JSON error details

5. **Frontend Polling** (`frontend/src/store/documentStore.ts`):
   - Frontend polls `GET /api/v1/documents/{doc_id}` to check processing status
   - Status determined by file existence (`.md` = ready, `.error` = failed)

**Critical Insight**: The system uses **file system as state database**. No database layer - document status is inferred from which files exist.

### GPU Device Detection Strategy

**Multi-layer fallback pattern** in `app/core/pdf_processor.py`:

```python
detect_device():
    1. Check PAPERREADER_DEVICE env var (manual override)
    2. Check torch.cuda.is_available()
    3. Fallback to 'cpu'
```

**Environment variable control**:
- `PAPERREADER_DEVICE=cuda` - force GPU
- `PAPERREADER_DEVICE=cpu` - force CPU
- Unset - auto-detect

**Graceful degradation** in `PDFProcessor.p2t` property:
- If GPU initialization fails, automatically retries with CPU
- Logs warning and updates `self.device` to 'cpu'

---

## Key Design Patterns

### 1. Lazy Loading Pattern (Pix2Text Model)

**Location**: `app/core/pdf_processor.py`

```python
class PDFProcessor:
    def __init__(self):
        self._p2t = None  # Not loaded yet

    @property
    def p2t(self):
        if self._p2t is None:
            from pix2text import Pix2Text
            self._p2t = Pix2Text.from_config(device=self.device)
        return self._p2t
```

**Why**: Pix2Text model download takes 1-2 minutes on first run. Lazy loading avoids blocking application startup.

### 2. Error Isolation Pattern

**Location**: `app/core/document_processor.py`

Failed document processing creates `.error` files instead of crashing:

```python
# data/processed/markdown/{doc_id}.error
{
  "error": "Error message",
  "error_type": "ProcessingError",
  "timestamp": "2026-01-12T18:30:00",
  "traceback": "Full stack trace..."
}
```

**Why**: Each document failure is isolated. Other documents continue processing. Frontend can display specific error messages.

### 3. Dual Store Pattern (Zustand)

**Location**: `frontend/src/store/`

**DocumentStore** - Business state:
```typescript
{
  documents: Document[],
  currentDocument: Document | null,
  isLoading: boolean,
  error: string | null,
  fetchDocuments(), uploadDocument(), deleteDocument()
}
```

**UIStore** - UI state:
```typescript
{
  isSidebarOpen: boolean,
  notification: Notification | null,
  toggleSidebar(), showNotification(), hideNotification()
}
```

**Why**: Separation of concerns. Business logic state independent of UI state. Stores can evolve independently.

### 4. Optimistic Update Pattern

**Location**: `frontend/src/store/documentStore.ts`

```typescript
uploadDocument: async (file) => {
  const tempId = 'temp-' + Date.now()
  // Immediately add to local state
  set({ documents: [...documents, { doc_id: tempId, status: 'uploading' }] })

  const result = await api.upload(file)
  // Update with real doc_id from server
  set({ documents: updatedWithRealId })
}
```

**Why**: Instant UI feedback. No waiting for server response before showing document in list.

### 5. Type Import Pattern

**Location**: Throughout frontend

```typescript
import type { Document } from '../types'  // ✅ Correct
import { Document } from '../types'        // ❌ Wrong with verbatimModuleSyntax
```

**Why**: TypeScript `verbatimModuleSyntax` requires `type` keyword for type-only imports.

### 6. DocumentStatus Enum (Critical for Frontend-Backend Sync)

**Location**: `frontend/src/types/document.ts`

The frontend and backend MUST use matching status values:

```typescript
export const DocumentStatus = {
  UPLOADING: 'uploading',    // Frontend-local state
  PROCESSING: 'processing',  // Backend: document being processed
  READY: 'ready',           // Backend: processing complete ✅ NOT 'completed'
  ERROR: 'error',           // Backend: processing failed ✅ NOT 'failed'
}
```

**Critical**: Backend returns `'ready'` and `'error'` - frontend must match exactly. Using `'completed'` or `'failed'` will break status display.

### 7. DocumentContent Type Matching

**Location**: `frontend/src/types/document.ts`

Backend API returns:
```json
{
  "doc_id": "uuid",
  "content": "Markdown text...",  // ✅ NOT 'markdown'
  "images": ["img_001", "img_002"],
  "status": "ready"
}
```

**TypeScript interface**:
```typescript
export interface DocumentContent {
  doc_id: string;
  content: string;      // ✅ Must be 'content', not 'markdown'
  images: string[];
  status: DocumentStatus;
  // ❌ NO 'filename', 'created_at' fields
}
```

### 8. Document Type Time Field

**Location**: `frontend/src/types/document.ts`

```typescript
export interface Document {
  doc_id: string;
  filename: string;
  status: DocumentStatus;
  upload_time: number;    // ✅ Unix timestamp (float), NOT string
  file_size: number;
  // ❌ NO 'file_type', 'updated_at' fields
}
```

**Usage**: Convert to display date with `new Date(doc.upload_time * 1000).toLocaleString()`

### 9. Polling with Exponential Backoff

**Location**: `frontend/src/hooks/useDocumentPolling.ts`

Document status polling uses exponential backoff to reduce server load:

```typescript
const calculateInterval = (count: number): number => {
  if (count < 10) return 3000;      // First 10: every 3s
  if (count < 30) return 5000;      // 10-30: every 5s
  return 10000;                     // After 30: every 10s
};
```

**Why**: Reduces unnecessary API calls while providing responsive status updates. Auto-stops when status reaches terminal state (`ready` or `error`).

### 10. DocumentViewer with Scroll Progress

**Location**: `frontend/src/components/DocumentViewer.tsx`

The document viewer displays scroll progress in real-time:

```typescript
useEffect(() => {
  const handleScroll = () => {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = (scrollTop / docHeight) * 100;
    setScrollProgress(Math.min(100, Math.max(0, progress)));
  };
  window.addEventListener('scroll', handleScroll);
  return () => window.removeEventListener('scroll', handleScroll);
}, []);
```

**Why**: Provides user feedback on reading progress. Clean up event listener on unmount prevents memory leaks.

### 11. Colored Logging System (Backend)

**Location**: `app/utils/logging_config.py`

Comprehensive logging system with emoji indicators and color-coded output:

```python
from app.utils.logging_config import setup_logging

# Initialize in app/main.py lifespan
setup_logging(log_level="INFO", log_file=None, use_color=True)

logger = logging.getLogger(__name__)
logger.info("ℹ️ Info message")   # White
logger.debug("🔍 Debug message") # Cyan
logger.warning("⚠️ Warning")     # Yellow
logger.error("❌ Error")         # Red
```

**Features**:
- Emoji prefixes for quick visual identification (ℹ️ 🔍 ⚠️ ❌ 🚨)
- Terminal color output (ANSI codes)
- Optional file logging with detailed debug info (function name, line number)
- Auto-configured third-party library noise reduction

**Log levels**:
- `DEBUG`: Detailed technical info (page scanning, image metadata, function params)
- `INFO`: Key business flow (file upload, processing complete, performance metrics)
- `WARNING`: Potential issues (image extraction failed, fallback to CPU)
- `ERROR`: Exception errors (processing failed, file corruption)

### 12. Performance Monitoring (Backend)

**Location**: `app/utils/performance.py`

Monitor execution time, memory usage, and CPU utilization:

```python
from app.utils.performance import monitor_performance

# Context manager (recommended)
with monitor_performance("PDF处理"):
    result = process_pdf()
# Auto-logs: 📊 [PERF] PDF处理 完成: time=38.57s, memory_delta=+125.3MB, cpu=12.3%

# Manual monitoring
monitor = PerformanceMonitor("操作名称")
monitor.start()
# ... do work ...
metrics = monitor.stop()  # Returns dict with elapsed_time, memory_delta_mb, cpu_percent
```

**Dependencies**: Requires `psutil>=5.9.0` and `Pillow>=10.0.0`

**Features**:
- Time measurement (high-precision)
- Memory delta calculation (RSS)
- CPU percentage during operation
- Graceful degradation if psutil not installed (falls back to time-only)

### 13. Detailed Image Extraction Logging

**Location**: `app/core/pdf_processor.py::_extract_images()`

Every extracted image logs comprehensive metadata:

```python
logger.info(
    f"🖼️ [PDF] 图像提取成功: "
    f"img_001, "
    f"xref=123, "
    f"size=800x600, "         # Width x Height
    f"format=PNG, "           # Format name (from PIL)
    f"mode=RGB, "             # Color mode (RGB, RGBA, L, etc.)
    f"bytes=156789, "         # File size in bytes
    f"page=1"                 # Page number
)
```

**Why**: Enables tracking of image quality issues, format problems, and processing bottlenecks.

### 14. Strategy Pattern (PDF Converters)

**Location**: `app/core/pdf_processor.py`, `app/core/converters/`

**Architecture**: Pluggable PDF converter selection via Strategy Pattern

```python
# Abstract Interface
class PDFConverterBase(ABC):
    @abstractmethod
    def convert_to_markdown(self, pdf_path, doc_id, output_base_dir) -> Tuple[str, List[str]]:
        pass

# Concrete Implementations
class Pix2TextConverter(PDFConverterBase):
    # Fast, formula-focused

class MarkerConverter(PDFConverterBase):
    # High-quality, layout-focused

# Facade with Dynamic Loading
class PDFProcessor:
    CONVERTERS = {
        "pix2text": "app.core.converters.pix2text_converter.Pix2TextConverter",
        "marker": "app.core.converters.marker_converter.MarkerConverter",
    }

    def __init__(self, converter: str = "pix2text"):
        self.converter_impl = self._load_converter(converter)  # Lazy loading

    def process(self, pdf_path, doc_id, output_base_dir):
        return self.converter_impl.convert_to_markdown(pdf_path, doc_id, output_base_dir)
```

**Benefits**:
- **Lazy Loading**: Only loads selected converter, saves memory
- **Graceful Degradation**: Auto-fallback to Pix2Text if Marker unavailable
- **Extensibility**: Add new converters without modifying existing code
- **Type Safety**: ConverterType enum ensures valid converter names

**Frontend Integration**:
```typescript
// User selects converter in dropdown
const [selectedConverter, setSelectedConverter] = useState<ConverterType>('pix2text');

// Pass to upload service
await uploadDocument(file, selectedConverter);
```

---

## Critical Implementation Details

### PDF Processing Architecture (Strategy Pattern)

**Location**: `app/core/pdf_processor.py`, `app/core/converters/`

The PDF processing system uses a **Strategy Pattern** with pluggable converters:

```
PDFProcessor (Facade)
    ↓
PDFConverterBase (Abstract Interface)
    ↓
├── Pix2TextConverter (Fast, formula-focused)
└── MarkerConverter (High-quality, layout-focused)
```

**Converter Selection** via API parameter:
```python
# Backend API
POST /api/v1/documents/upload?converter=pix2text  # Default
POST /api/v1/documents/upload?converter=marker    # High quality
```

**Frontend Selection** via dropdown in `FileUpload.tsx`:
- **Pix2Text**: 3-5 sec/page, ~500MB VRAM, best for academic papers
- **Marker**: 8-15 sec/page, ~5GB VRAM, best for complex layouts/tables

**Graceful Degradation**:
- If `marker-pdf` not installed, automatically falls back to `pix2text`
- If GPU initialization fails, automatically retries with CPU
- Logged warning: `⚠️ marker-pdf未安装,自动降级到pix2text`

**Adding New Converters**:
1. Create `app/core/converters/new_converter.py` inheriting `PDFConverterBase`
2. Implement `convert_to_markdown(pdf_path, doc_id, output_base_dir) -> (markdown, images)`
3. Add to `PDFProcessor.CONVERTERS` dict
4. Add to `app/models/document.py` `ConverterType` enum
5. Update frontend `CONVERTER_OPTIONS` in `types/document.ts`

### Token Management Strategy

**Location**: `app/core/context_builder.py` (Phase 3 - planned)

Qwen supports 128k context. Strategy:
- MAX_TOKENS = 120,000 (8k buffer for prompt + response)
- Smart truncation prioritizes: Abstract → Introduction → Conclusion → Methods → References
- Uses tiktoken for accurate token counting

### Configuration Management

**Location**: `app/config.py`

```python
class Settings(BaseSettings):
    dashscope_api_key: str  # Required from env
    api_host: str = "127.0.0.1"
    upload_dir: Path = Path("./data/uploads")

    # GPU控制
    paperreader_device: str = "auto"  # auto/cuda/cpu

    # 日志配置
    log_level: str = "INFO"          # DEBUG/INFO/WARNING/ERROR
    log_file: Path = None            # None=终端 only, or Path("logs/app.log")
    log_use_color: bool = True       # Terminal color output

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
```

**Key points**:
- Type-safe configuration via Pydantic
- Reads from environment variables and `.env` file
- Extra variables in `.env` are ignored (`extra="ignore"`)
- **Logging**: Control log verbosity via `LOG_LEVEL` env var
- **Log file**: Set `LOG_FILE=data/logs/app.log` to enable file logging

### API Route Pattern

**Location**: `app/api/v1/`, `app/main.py`

All routes follow RESTful conventions:

```python
# app/api/v1/documents.py
router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # Implementation

# Registered in app/main.py
app.include_router(
    documents.router,
    prefix=settings.api_prefix,  # /api/v1
    tags=["documents"]
)
```

**File paths**:
- Routes: `app/api/v1/{feature}.py`
- Models: `app/models/{feature}.py` (Pydantic schemas)
- Business logic: `app/core/{feature}_processor.py`

### Frontend Dependencies

**Location**: `frontend/package.json`

Key Phase 2 dependencies:
- `react-markdown`: Markdown rendering
- `remark-math` + `rehype-katex`: LaTeX formula support
- `remark-gfm`: GitHub Flavored Markdown (tables, strikethrough)
- `react-router-dom`: Client-side routing (v7)
- `zustand`: State management
- `axios`: HTTP client
- `katex`: Math formula rendering

**Installation**:
```bash
cd frontend
npm install react-markdown remark-math rehype-katex remark-gfm react-router-dom zustand axios katex
```

---

## Important File Locations

### Backend Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app entry point, CORS, route registration, logging init |
| `app/config.py` | Pydantic Settings configuration (includes log settings) |
| `app/api/v1/documents.py` | Document upload/list/delete endpoints with detailed logs |
| `app/core/pdf_processor.py` | **PDF Processor Facade** - dynamic converter selection |
| `app/core/converters/base.py` | **PDFConverterBase** - abstract interface for converters |
| `app/core/converters/pix2text_converter.py` | Pix2Text implementation (fast, formula-focused) |
| `app/core/converters/marker_converter.py` | Marker implementation (high-quality, layout-focused) |
| `app/core/document_processor.py` | Background task coordination, performance metrics |
| `app/models/document.py` | **ConverterType** enum for converter selection |
| `app/utils/logging_config.py` | **Colored logging system** (emoji, color-coded levels) |
| `app/utils/performance.py` | **Performance monitoring** (time, memory, CPU) |
| `data/uploads/{doc_id}/original.pdf` | Original uploaded files |
| `data/processed/markdown/{doc_id}.md` | Processed Markdown output |
| `data/processed/images/{doc_id}/` | Extracted images |
| `backend/test_logging.py` | **Logging system test script** |

### Frontend Key Files

| File | Purpose |
|------|---------|
| `src/App.tsx` | Router setup with RouterProvider |
| `src/router/index.tsx` | Route configuration (react-router-dom v7) |
| `src/types/document.ts` | **ConverterType, CONVERTER_OPTIONS** - PDF converter selection |
| `src/services/client.ts` | Axios instance configuration |
| `src/services/document.ts` | Document API service (uploadDocument accepts converter param) |
| `src/store/documentStore.ts` | Document state management (uploadDocument with converter) |
| `src/store/uiStore.ts` | UI state (sidebar, notifications) |
| `src/hooks/useDocumentPolling.ts` | Document status polling with exponential backoff |
| `src/components/FileUpload.tsx` | **Upload with converter dropdown** (drag-and-drop) |
| `src/components/DocumentList.tsx` | Document list with status badges |
| `src/components/MarkdownRenderer.tsx` | Markdown + LaTeX rendering (react-markdown + KaTeX) |
| `src/components/LazyImage.tsx` | Image lazy loading with Intersection Observer |
| `src/components/DocumentViewer.tsx` | Document viewer with scroll progress |
| `src/pages/HomePage.tsx` | Home page |
| `src/pages/DocumentViewPage.tsx` | Document view page |

---

## Development Workflow

### Adding Backend Features

1. **Create route** in `app/api/v1/{feature}.py`:
   ```python
   router = APIRouter(prefix="/feature", tags=["feature"])

   @router.post("/")
   async def create_feature(request: RequestSchema):
       # Call business logic
       pass
   ```

2. **Define models** in `app/models/{feature}.py`:
   ```python
   class RequestSchema(BaseModel):
       field: str
   ```

3. **Implement business logic** in `app/core/{feature}_processor.py`:
   ```python
   class FeatureProcessor:
       def process(self, input) -> output:
           pass
   ```

4. **Register route** in `app/main.py`:
   ```python
   app.include_router(feature.router, prefix=settings.api_prefix)
   ```

5. **Add tests** in `tests/test_{feature}.py`

### Adding Frontend Features

1. **Create component** in `src/components/{Feature}.tsx`:
   ```typescript
   import type { FeatureData } from '../types'

   export const Feature: React.FC<{ data: FeatureData }> = ({ data }) => {
     return <div>{data.field}</div>
   }
   ```

2. **Add API service** in `src/services/{feature}.ts`:
   ```typescript
   export class FeatureService {
     async getFeature(): Promise<FeatureData> {
       return apiClient.get('/feature')
     }
   }
   ```

3. **Update store** in `src/store/{feature}Store.ts` (if needed):
   ```typescript
   export const useFeatureStore = create<FeatureState>((set) => ({
     data: null,
     fetchData: async () => { /* ... */ }
   }))
   ```

4. **Add types** in `src/types/{feature}.ts`

5. **Add route** in `src/router/index.tsx` (if creating new page):
   ```typescript
   import { NewFeaturePage } from '../pages/NewFeaturePage';

   // In router config:
   {
     path: 'feature/:id',
     element: <NewFeaturePage />,
   }
   ```

6. **Create page component** in `src/pages/{Feature}Page.tsx`:
   ```typescript
   export const FeaturePage: React.FC = () => {
     const { id } = useParams<{ id: string }>();
     const navigate = useNavigate();
     // Component logic
   };
   ```

### Debugging Tips

**Backend**:
- Use Swagger UI at http://localhost:8000/api/docs for API testing
- Check `data/processed/markdown/{doc_id}.error` for processing failures
- **Test logging system**: `python test_logging.py` (validates colored output, performance monitoring)
- Enable logging: `logger.info()`, `logger.error()` throughout code
- Test device detection: `python -c "from app.core.pdf_processor import detect_device; print(detect_device())"`
- **Adjust log level**: Set `LOG_LEVEL=DEBUG` in `.env` for detailed output
- **Enable file logging**: Set `LOG_FILE=data/logs/app.log` in `.env`

**Frontend**:
- Browser DevTools → Network tab: View API requests/responses
- React DevTools: Inspect component tree and state
- Console: Check for `console.log()` output and errors
- Type checking: `npx tsc --noEmit` to find type errors
- **Route debugging**: Check `src/router/index.tsx` for route configuration
- **Polling debugging**: Check `useDocumentPolling` hook logs and interval timing
- **State debugging**: Use Zustand DevTools middleware (if configured)

---

## Common Gotchas

### Pix2Text First Load
- **Issue**: First Pix2Text call takes 1-2 minutes (model download)
- **Solution**: Lazy loading via `@property` mitigates this. Only impacts first document processed after server start.

### Environment Variable Precedence
- **Issue**: `DASHSCOPE_API_KEY` must be set before importing `app.config`
- **Solution**: Set in system environment or `.env` file before starting server
- **Verify**: `python -c "from app.config import settings; print(settings.dashscope_api_key[:10])"`

### Windows Path Handling
- **Issue**: Backslash path separators cause issues
- **Solution**: Use forward slashes `/` or double backslashes `\\` in paths
- **Virtual env activation**: PowerShell uses `.\venv\Scripts\Activate.ps1`

### CORS Configuration
- **Issue**: Frontend at `localhost:5173` cannot reach backend at `localhost:8000`
- **Solution**: Ensure `http://localhost:5173` is in `settings.cors_origins` in `app/config.py`

### TypeScript Type Imports
- **Issue**: Import errors with `verbatimModuleSyntax` enabled
- **Solution**: Use `import type { ... }` for type-only imports

### File System State Race Conditions
- **Issue**: Frontend polls for status before file is created
- **Solution**: Frontend implements retry logic. Status endpoint returns appropriate HTTP codes.

### CSS @import Order
- **Issue**: PostCSS error: "@import must precede all other statements"
- **Solution**: `@import` statements must come FIRST in CSS files, before `@tailwind` directives
- **Example**:
  ```css
  /* ✅ Correct */
  @import 'katex/dist/katex.min.css';
  @tailwind base;
  @tailwind components;
  @tailwind utilities;

  /* ❌ Wrong */
  @tailwind base;
  @import 'katex/dist/katex.min.css';
  ```

### JSX Comment Placement
- **Issue**: TypeScript error with comments inside JSX expressions
- **Solution**: Comments must be OUTSIDE the expression or use separate `{/* */}` blocks
- **Example**:
  ```tsx
  {/* ✅ Correct - Comment outside */}
  {doc.status === 'ready' && (
    <button>View</button>
  )}

  {/* ❌ Wrong - Comment inside opening */}
  {doc.status === 'ready' && (  {/* comment */}
    <button>View</button>
  )}
  ```

### setInterval Return Type in Browser
- **Issue**: `NodeJS.Timeout` type error in browser environment
- **Solution**: Use `ReturnType<typeof setInterval>` or `number | undefined` for ref
- **Example**:
  ```typescript
  const intervalRef = useRef<number | undefined>(undefined);
  intervalRef.current = setInterval(callback, 1000);
  ```

### Log Output Too Verbose
- **Issue**: DEBUG logs cluttering the console
- **Solution**: Set `LOG_LEVEL=INFO` in `.env` file (production recommended)
- **For development**: Use `LOG_LEVEL=DEBUG` to see page-by-page processing details

### Performance Monitoring Not Working
- **Issue**: Memory/CPU metrics showing as None or missing
- **Solution**: Install `psutil`: `pip install psutil>=5.9.0`
- **Fallback**: System automatically degrades to time-only monitoring if psutil unavailable

### PIL Image Extraction Fails
- **Issue**: `PIL` or `Pillow` not found errors during image metadata extraction
- **Solution**: Install Pillow: `pip install Pillow>=10.0.0`
- **Fallback**: System uses basic metadata (width/height from PyMuPDF) if PIL unavailable

### Marker Converter Not Available
- **Issue**: User selects "Marker" converter but gets automatic fallback to Pix2Text
- **Solution**: Install marker-pdf: `pip install marker-pdf>=0.2.6`
- **Requirements**: Marker needs 5GB+ GPU VRAM, Python 3.10+, PyTorch 2.7.0+
- **Fallback**: System logs warning and uses Pix2Text automatically if Marker unavailable
- **Check logs**: Look for `⚠️ marker-pdf未安装,自动降级到pix2text`

### Converter Parameter Missing
- **Issue**: Frontend doesn't send converter parameter, API returns 422 error
- **Solution**: Ensure frontend passes `formData.append('converter', converter)` in uploadDocument
- **Default value**: Backend defaults to `pix2text` if parameter not provided
- **Type check**: Verify ConverterType enum matches between backend (`app/models/document.py`) and frontend (`src/types/document.ts`)

---

## Related Documentation

- **README.md**: Project overview, features, installation guide (user-facing)
- **devplan.md**: Complete development roadmap and phase planning
- **devplan_phase2_frontend.md**: Phase 2 frontend implementation details (Markdown rendering, routing, polling)
- **devplan_phase2_marker.md**: Phase 2 Marker PDF converter architecture (Strategy Pattern implementation)
- **backend/CLAUDE.md**: Backend-specific deep-dive
- **API Docs**: http://localhost:8000/api/docs (Swagger UI when backend running)
