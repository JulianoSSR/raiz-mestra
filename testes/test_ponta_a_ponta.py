"""Ensaio automático do fluxo E1: dossiê -> entrega -> rotular -> lint -> fechar.

O `dossie.py marcar <slug> entrega` confere a entrega antes de gravar o passo:
exige `--evidencia` com arquivo existente, roda `rotular.py` e `lint_entrega.py`
(com cada `--pesquisa` repassado ao lint) e grava o sha256 do arquivo conferido.
Os testes abaixo provam a trava: entrega ruim, ausente ou sem evidência não
marca o passo. Os verificadores são heurísticos: passar aqui não prova que a
entrega está certa.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
FIX = RAIZ / "testes" / "fixtures"
SLUG = "padaria"


class TestPontaAPonta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = dict(os.environ, RAIZ_MESTRA_DADOS=self.tmp.name)

    def py(self, script, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                           capture_output=True, text=True, env=self.env, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def dossie(self, *args):
        return self.py("dossie.py", *args)

    def pasta(self):
        return Path(self.tmp.name) / "dossies" / SLUG

    def prepara(self):
        self.assertEqual(self.dossie("init", SLUG)[0], 0)
        self.assertEqual(self.dossie("responder", SLUG, "tamanho", "E2")[0], 0)
        self.assertEqual(self.dossie("responder", SLUG, "eleitoral", "não")[0], 0)

    def test_caminho_feliz(self):
        self.prepara()
        evid = Path(self.tmp.name) / "evidencia.txt"
        evid.write_text("ok", encoding="utf-8")
        for passo in ("triagem", "levantamento", "mapa", "conceitos", "pre-mortem"):
            rc, out = self.dossie("marcar", SLUG, passo, "--evidencia", evid)
            self.assertEqual(rc, 0, out)
        entrega = self.pasta() / "entrega.md"
        shutil.copy(FIX / "boas" / "entrega-exemplo.md", entrega)
        rc, out = self.py("rotular.py", entrega)
        self.assertEqual(rc, 0, out)
        rc, out = self.py("lint_entrega.py", entrega)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)[0], 0)
        self.assertEqual(self.dossie("responder", SLUG, "aprendizado", "nada a propor")[0], 0)
        rc, out = self.dossie("marcar", SLUG, "aprendizado", "--evidencia", evid)
        self.assertEqual(rc, 0, out)
        rc, out = self.dossie("fechar", SLUG)
        self.assertEqual(rc, 0, out)
        rc, out = self.dossie("estado", SLUG)
        self.assertIn('"entrega"', out)
        self.assertNotIn('"fechado": null', out)

    def test_nao_fecha_sem_aprendizado(self):
        self.prepara()
        rc, out = self.dossie("fechar", SLUG)
        self.assertEqual(rc, 1, out)
        self.assertIn("aprendizado", out)
        self.assertIn('"fechado": null', self.dossie("estado", SLUG)[1])

    def test_nao_passa_da_triagem_sem_tamanho_e_eleitoral(self):
        self.assertEqual(self.dossie("init", SLUG)[0], 0)
        rc, out = self.dossie("marcar", SLUG, "levantamento")
        self.assertEqual(rc, 1, out)

    def test_entrega_ruim_reprova_nos_dois_scripts(self):
        self.prepara()
        entrega = self.pasta() / "entrega.md"
        shutil.copy(FIX / "ruins" / "maioria-compraria.md", entrega)
        self.assertEqual(self.py("rotular.py", entrega)[0], 0)  # forma ok
        rc, out = self.py("lint_entrega.py", entrega)
        self.assertEqual(rc, 1, out)
        shutil.copy(FIX / "ruins" / "secao-ausente.md", entrega)
        self.assertEqual(self.py("rotular.py", entrega)[0], 1)

    def estado(self):
        rc, out = self.dossie("estado", SLUG)
        self.assertEqual(rc, 0, out)
        return json.loads(out)

    def entrega_de(self, fixture):
        entrega = self.pasta() / "entrega.md"
        shutil.copy(FIX / fixture, entrega)
        return entrega

    def test_entrega_ruim_de_lint_nao_marca(self):
        self.prepara()
        entrega = self.entrega_de("ruins/maioria-compraria.md")
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)
        self.assertEqual(rc, 1, out)
        self.assertIn("lint_entrega.py", out)
        self.assertIn("a maioria", out)  # a saída do verificador aparece
        self.assertNotIn("entrega", self.estado()["passos"])

    def test_entrega_ruim_de_rotulo_nao_marca(self):
        self.prepara()
        entrega = self.entrega_de("ruins/secao-ausente.md")
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)
        self.assertEqual(rc, 1, out)
        self.assertIn("rotular.py", out)
        self.assertIn("seção ausente", out)
        self.assertNotIn("entrega", self.estado()["passos"])

    def test_entrega_sem_evidencia_nao_marca(self):
        self.prepara()
        rc, out = self.dossie("marcar", SLUG, "entrega")
        self.assertEqual(rc, 1, out)
        self.assertIn("--evidencia", out)
        self.assertNotIn("entrega", self.estado()["passos"])

    def test_entrega_com_evidencia_inexistente_nao_marca(self):
        self.prepara()
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", self.pasta() / "nao-existe.md")
        self.assertEqual(rc, 1, out)
        self.assertNotIn("entrega", self.estado()["passos"])
        # pasta não é arquivo comum
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", self.pasta())
        self.assertEqual(rc, 1, out)
        self.assertNotIn("entrega", self.estado()["passos"])

    def test_entrega_boa_marca_e_grava_sha256(self):
        self.prepara()
        entrega = self.entrega_de("boas/entrega-exemplo.md")
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)
        self.assertEqual(rc, 0, out)
        passo = self.estado()["passos"]["entrega"]
        self.assertRegex(passo["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(passo["sha256"], hashlib.sha256(entrega.read_bytes()).hexdigest())
        self.assertEqual(passo["evidencia"], str(entrega))
        self.assertIn("em", passo)

    def test_entrega_ja_marcada_nao_reconfere(self):
        self.prepara()
        entrega = self.entrega_de("boas/entrega-exemplo.md")
        self.assertEqual(self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)[0], 0)
        antes = self.estado()["passos"]["entrega"]
        shutil.copy(FIX / "ruins" / "maioria-compraria.md", entrega)
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)
        self.assertEqual(rc, 0, out)
        self.assertIn("já estava marcado", out)
        self.assertEqual(self.estado()["passos"]["entrega"], antes)

    def test_outros_passos_seguem_sem_sha256(self):
        self.prepara()
        self.assertEqual(self.dossie("marcar", SLUG, "conceitos")[0], 0)
        self.assertEqual(self.estado()["passos"]["conceitos"].keys(), {"em", "evidencia"})

    def test_pesquisa_e_repassada_ao_lint(self):
        fonte = FIX / "pesquisa" / "fonte-pesquisa.md"
        self.prepara()
        entrega = self.entrega_de("ruins/trecho-copiado.md")
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega, "--pesquisa", fonte)
        self.assertEqual(rc, 1, out)
        self.assertIn("trecho copiado", out)
        self.assertNotIn("entrega", self.estado()["passos"])
        # duas fontes: a segunda também chega ao lint
        limpa = Path(self.tmp.name) / "outra-fonte.md"
        limpa.write_text("Texto sem relação com a entrega.\n", encoding="utf-8")
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega,
                              "--pesquisa", limpa, "--pesquisa", fonte)
        self.assertEqual(rc, 1, out)
        self.assertNotIn("entrega", self.estado()["passos"])
        # pesquisa inexistente também não marca
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega,
                              "--pesquisa", Path(self.tmp.name) / "sumiu.md")
        self.assertEqual(rc, 1, out)
        self.assertNotIn("entrega", self.estado()["passos"])
        # sem --pesquisa, a mesma entrega passa
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)
        self.assertEqual(rc, 0, out)
        self.assertIn("entrega", self.estado()["passos"])

    def test_pesquisa_fora_da_entrega_e_uso_errado(self):
        self.prepara()
        evid = Path(self.tmp.name) / "evidencia.txt"
        evid.write_text("ok", encoding="utf-8")
        rc, out = self.dossie("marcar", SLUG, "conceitos", "--evidencia", evid,
                              "--pesquisa", FIX / "pesquisa" / "fonte-pesquisa.md")
        self.assertEqual(rc, 2, out)
        self.assertIn("uso:", out)
        self.assertNotIn("conceitos", self.estado()["passos"])

    def test_entrega_com_eleitoral_diferente_da_resposta_nao_marca(self):
        self.prepara()  # resposta eleitoral: não
        self.assertEqual(self.dossie("responder", SLUG, "eleitoral", "sim")[0], 0)
        entrega = self.entrega_de("boas/entrega-exemplo.md")  # cabeçalho: eleitoral: não
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)
        self.assertEqual(rc, 1, out)
        self.assertIn("eleitoral", out)
        self.assertNotIn("entrega", self.estado()["passos"])

    def test_entrega_com_tamanho_diferente_da_resposta_nao_marca(self):
        self.prepara()  # resposta tamanho: E2
        self.assertEqual(self.dossie("responder", SLUG, "tamanho", "E3")[0], 0)
        entrega = self.entrega_de("boas/entrega-exemplo.md")
        texto = entrega.read_text(encoding="utf-8").replace("tamanho: E2", "tamanho: E1", 1)
        entrega.write_text(texto, encoding="utf-8")  # cabeçalho: tamanho: E1
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)
        self.assertEqual(rc, 1, out)
        self.assertIn("tamanho", out)
        self.assertNotIn("entrega", self.estado()["passos"])

    def test_entrega_sem_linha_de_cabecalho_da_resposta_nao_marca(self):
        self.prepara()  # resposta eleitoral: não
        entrega = self.entrega_de("boas/entrega-exemplo.md")
        texto = "".join(l for l in entrega.read_text(encoding="utf-8").splitlines(True)
                        if not l.startswith("eleitoral:"))
        entrega.write_text(texto, encoding="utf-8")
        rc, out = self.dossie("marcar", SLUG, "entrega", "--evidencia", entrega)
        self.assertEqual(rc, 1, out)
        self.assertIn("eleitoral", out)
        self.assertNotIn("entrega", self.estado()["passos"])

    def test_valor_do_ambiente_nao_aparece_na_saida(self):
        casa = Path(self.tmp.name) / "SENTINELA_CASA_7f3a"
        base = Path(self.tmp.name) / "SENTINELA_DADOS_7f3a"
        fora = Path(self.tmp.name) / "fora"
        fora.mkdir()
        self.env = dict(os.environ, RAIZ_MESTRA_DADOS=str(base), RAIZ_MESTRA_CHAVE_API="SENTINELA_CHAVE_7f3a",
                        HOME=str(casa), USERPROFILE=str(casa))
        saidas = []

        def roda(*args):
            rc, out = self.dossie(*args)
            saidas.append(out)
            return rc

        self.assertEqual(roda("init", SLUG), 0)
        (base / "dossies" / SLUG / "estado.json").write_text('{"slug": "padaria", "passos": {', encoding="utf-8")
        self.assertEqual(roda("estado", SLUG), 1)
        self.assertEqual(roda("marcar", SLUG, "triagem"), 1)
        self.assertEqual(roda("init", "outra"), 0)
        self.assertEqual(roda("responder", "outra", "tamanho", "E1"), 0)
        self.assertEqual(roda("responder", "outra", "eleitoral", "não"), 0)
        self.assertEqual(roda("marcar", "outra", "entrega", "--evidencia", casa / "nao-existe.md"), 1)
        (base / "dossies" / "preso").symlink_to(fora)
        self.assertEqual(roda("init", "preso"), 1)
        for script in sorted(SCRIPTS.glob("*.py")):
            if script.name in ("ambiente.py", "__init__.py"):
                continue
            r = subprocess.run([sys.executable, "-B", str(script)], capture_output=True, text=True,
                               env=self.env, timeout=60, stdin=subprocess.DEVNULL)
            saidas.append(r.stdout + r.stderr)
        for out in saidas:
            self.assertNotIn("SENTINELA", out)
            self.assertNotIn(str(base), out)
            self.assertNotIn(str(casa), out)
            self.assertNotIn(str(fora), out)


if __name__ == "__main__":
    unittest.main()
