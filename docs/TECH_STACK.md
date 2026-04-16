# Tech Stack — שמאי מכריע

## Backend
| Layer | Technology | Version |
|-------|-----------|---------|
| Web framework | FastAPI | 0.115.6 |
| ASGI server | Uvicorn | 0.34.0 |
| HTTP client | httpx | 0.28.1 |
| PDF parsing | pdfplumber | 0.11.4 |
| OCR wrapper | pytesseract | 0.3.13 |
| PDF→image | pdf2image | 1.17.0 |
| Image processing | Pillow | 11.1.0 |
| AI | anthropic SDK | 0.49.0 |
| Config | python-dotenv | 1.0.1 |
| Database | SQLite (built-in) + FTS5 | — |

## System Dependencies
| Dependency | Purpose |
|-----------|---------|
| Tesseract OCR | PDF text extraction (Hebrew language pack required) |
| Python 3.10+ | Runtime |

## Frontend
| Layer | Technology |
|-------|-----------|
| UI | Vanilla HTML/CSS/JS — no framework |
| Direction | RTL (Hebrew) |
| Streaming | Server-Sent Events (EventSource) |
| Fonts | System default |

## External APIs
| API | Purpose | Auth |
|-----|---------|------|
| MoJ SearchDecisions | Search and download decisions | `x-client-id` header (public) |
| Anthropic Claude | Document analysis (optional) | `ANTHROPIC_API_KEY` |

## Infrastructure
| Component | Current | Production Option |
|-----------|---------|------------------|
| Hosting | Local only | Hetzner CX22 (~€4/mo) |
| Storage | Local filesystem | Persistent VPS disk |
| Database | Local SQLite | Same (SQLite sufficient for this scale) |
| SSL | None | Let's Encrypt via nginx |
| Process manager | Manual uvicorn | systemd |
