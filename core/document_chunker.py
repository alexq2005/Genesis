"""
GENESIS — Smart Chunker.

Divide documentos en chunks optimizados para LLMs.
Usa overlap por párrafos para mantener contexto entre chunks.
"""
import re


class SmartChunker:
    """
    Divide documentos en chunks optimizados para Llama 3.1 8B.

    Chrome Speech bug analog: asi como Chrome corta speech despues de 15s,
    Llama 3.1 8B pierde coherencia con contextos muy largos. Chunks de
    ~2048 tokens mantienen la calidad de analisis.
    """

    def __init__(self, max_chunk_tokens: int = 2048, overlap_tokens: int = 200):
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
        # Español promedio: ~3.5 chars por token con Llama tokenizer
        self.chars_per_token = 3.5

    def chunk(self, text: str, source: str = "") -> list:
        """
        Divide texto en chunks con overlap.

        Returns:
            Lista de {text, chunk_id, token_estimate, source, start_char, end_char}
        """
        if not text or not text.strip():
            return []

        max_chars = int(self.max_chunk_tokens * self.chars_per_token)
        overlap_chars = int(self.overlap_tokens * self.chars_per_token)

        # Si el texto cabe en un solo chunk, retornar directo
        if len(text) <= max_chars:
            return [{
                "text": text,
                "chunk_id": 0,
                "token_estimate": self._estimate_tokens(text),
                "source": source,
                "start_char": 0,
                "end_char": len(text),
            }]

        chunks = []
        # Dividir por parrafos primero
        paragraphs = re.split(r'\n{2,}', text)

        current_chunk = ""
        chunk_start = 0
        char_pos = 0

        for para in paragraphs:
            para_with_sep = para + "\n\n"

            if len(current_chunk) + len(para_with_sep) <= max_chars:
                current_chunk += para_with_sep
            else:
                # Guardar chunk actual
                if current_chunk.strip():
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_id": len(chunks),
                        "token_estimate": self._estimate_tokens(current_chunk),
                        "source": source,
                        "start_char": chunk_start,
                        "end_char": chunk_start + len(current_chunk),
                    })

                # Overlap: tomar las ultimas N chars del chunk anterior
                if current_chunk and overlap_chars > 0:
                    overlap_text = current_chunk[-overlap_chars:]
                    # Cortar en limite de oracion si es posible
                    sentence_break = overlap_text.find(". ")
                    if sentence_break > 0:
                        overlap_text = overlap_text[sentence_break + 2:]
                    chunk_start = chunk_start + len(current_chunk) - len(overlap_text)
                    current_chunk = overlap_text + para_with_sep
                else:
                    chunk_start += len(current_chunk)
                    current_chunk = para_with_sep

                # Si un solo parrafo es mayor que max_chars, dividir por oraciones
                if len(current_chunk) > max_chars:
                    sub_chunks = self._split_long_paragraph(current_chunk, max_chars)
                    for sc in sub_chunks[:-1]:
                        chunks.append({
                            "text": sc.strip(),
                            "chunk_id": len(chunks),
                            "token_estimate": self._estimate_tokens(sc),
                            "source": source,
                            "start_char": chunk_start,
                            "end_char": chunk_start + len(sc),
                        })
                        chunk_start += len(sc)
                    current_chunk = sub_chunks[-1] if sub_chunks else ""

        # Ultimo chunk
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_id": len(chunks),
                "token_estimate": self._estimate_tokens(current_chunk),
                "source": source,
                "start_char": chunk_start,
                "end_char": chunk_start + len(current_chunk),
            })

        return chunks

    def _split_long_paragraph(self, text: str, max_chars: int) -> list:
        """Divide un parrafo largo por oraciones."""
        sentences = re.split(r'(?<=[.!?;:])\s+', text)
        parts = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_chars:
                current = (current + " " + sentence).strip()
            else:
                if current:
                    parts.append(current)
                # Si una sola oracion es muy larga, cortar por comas
                if len(sentence) > max_chars:
                    comma_parts = sentence.split(", ")
                    sub = ""
                    for cp in comma_parts:
                        if len(sub) + len(cp) + 2 <= max_chars:
                            sub = (sub + ", " + cp).strip(", ")
                        else:
                            if sub:
                                parts.append(sub)
                            sub = cp
                    current = sub
                else:
                    current = sentence

        if current:
            parts.append(current)
        return parts

    def _estimate_tokens(self, text: str) -> int:
        """Estima tokens para texto en español (~3.5 chars/token)."""
        return int(len(text) / self.chars_per_token)
