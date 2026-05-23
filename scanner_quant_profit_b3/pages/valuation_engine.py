"""Página Valuation Engine — análise fundamentalista."""
import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON" / "pipeline banco completo"

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from streamlit_app import main as _streamlit_main

    def main() -> None:
        _streamlit_main(skip_page_config=True)

except Exception as exc:
    import streamlit as st
    st.set_page_config(page_title="Valuation Engine", page_icon="")
    st.markdown("""
    <div style="background:#0D1421;border:1px solid #1E3A52;border-radius:12px;
                padding:32px;max-width:640px;margin:40px auto;text-align:center">
      <div style="font-size:2rem;margin-bottom:12px">&#9888;</div>
      <h2 style="color:#F1F5F9;font-family:var(--font-display)">Pipeline Externo Indisponivel</h2>
      <p style="color:#94A3B8;line-height:1.6">
        A pagina <strong>Valuation Engine</strong> depende do pipeline externo
        <code>12_PYTHON/pipeline banco completo/streamlit_app.py</code>.
      </p>
      <p style="color:#64748B;font-size:0.85rem">
        Erro: {exc}
      </p>
      <p style="color:#475569;font-size:0.82rem;margin-top:16px">
        Execute o pipeline externo separadamente ou mapeie o modulo para o PYTHONPATH.
      </p>
    </div>
    """.format(exc=type(exc).__name__), unsafe_allow_html=True)

    def main() -> None:
        pass
import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON" / "pipeline banco completo"

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from streamlit_app import main
main(skip_page_config=True)
