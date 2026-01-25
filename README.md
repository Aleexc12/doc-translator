# PDF Translator

A Python toolkit for translating PDF documents from **English to Spanish** while preserving the original layout and structure.

![Demo](demo_images/demo3.jpg)

## Features

- **Layout Preservation**: Maintains original document structure (paragraphs, titles, captions, footnotes)
- **Multiple Extraction Methods**: Fast mode for simple PDFs, accurate mode for complex documents
- **Multiple Translation Backends**: OpenAI API or free local MarianMT models
- **Formula Preservation**: LaTeX formulas and equations remain intact
- **Smart Caching**: Reduces API costs by caching translations

## Installation

```bash
# Clone the repository
git clone https://github.com/Aleexc12/doc-translator.git
cd doc-translator

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (for OpenAI)
cp .env.example .env
# Edit .env with your OpenAI API key
```

## Usage

It's recommended to place your PDFs in the `pdfs/` folder for organization. There are 3 demo PDFs included for testing.

```bash
python translate_cli.py demo1.pdf
```

The CLI will automatically search in `pdfs/` if the file isn't found in the root directory.

**Output:** Translated PDFs are saved to `output_pdfs/`

### Other Use Cases

#### Simple Text PDFs (Fast)

For straightforward documents with simple layouts:

```bash
# OpenAI (best quality)
python translate_cli.py demo1.pdf --extractor pymupdf

# MarianMT (free, no API key)
python translate_cli.py demo1.pdf --extractor pymupdf --translator marianmt
```

#### Complex Documents (Accurate)

For academic papers, technical documents with formulas, tables, or complex layouts:

```bash
# OpenAI (best quality)
python translate_cli.py demo1.pdf

# MarianMT (free, no API key)
python translate_cli.py demo1.pdf --translator marianmt
```

### Options

| Option | Description |
|--------|-------------|
| `--extractor pymupdf` | Fast extraction for simple text PDFs |
| `--extractor mineru` | Accurate extraction for complex layouts (default) |
| `--translator openai` | OpenAI translation, best quality (default) |
| `--translator marianmt` | Free local translation, no API key needed |
| `--f` | Force re-extraction (ignore cache) |

## Requirements

- Python 3.11+
- OpenAI API key (optional, for OpenAI translator)
- GPU recommended for MarianMT (works on CPU too, just slower)

## TODO

- [ ] True text replacement (current overlay method preserves original text in PDF structure)
- [ ] Support for local LLMs (Ollama, llama.cpp)
- [ ] Multi-language support (currently English to Spanish only)
- [ ] Support for inline formulas



## License

MIT License

## Acknowledgments

- [MinerU](https://github.com/opendatalab/MinerU) for document structure extraction
- [Helsinki-NLP](https://huggingface.co/Helsinki-NLP) for MarianMT models

