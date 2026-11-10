import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dados  # noqa: E402
import dossie  # noqa: E402


class TestDossie(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.dict(os.environ, {"RAIZ_MESTRA_DADOS": self.tmp.name})
        p.start()
        self.addCleanup(p.stop)
        dossie.init("caso")

    def run_main(self, *a):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = dossie.main(list(a))
        return rc, buf.getvalue()

    def responder_tudo(self):
        dossie.responder("caso", "tamanho", "E1")
        dossie.responder("caso", "eleitoral", "não")

    def test_init_e_estado(self):
        rc, out = self.run_main("estado", "caso")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["slug"], "caso")

    def test_init_duplicado(self):
        rc, _ = self.run_main("init", "caso")
        self.assertEqual(rc, 1)

    def test_slug_invalido(self):
        rc, _ = self.run_main("init", "../x")
        self.assertEqual(rc, 1)

    def test_marcar_idempotente(self):
        self.assertTrue(dossie.marcar("caso", "triagem", "a.md"))
        antes = dossie.carregar("caso")["passos"]["triagem"]
        self.assertFalse(dossie.marcar("caso", "triagem", "b.md"))
        self.assertEqual(dossie.carregar("caso")["passos"], {"triagem": antes})
        self.assertIn("em", antes)
        self.assertEqual(antes["evidencia"], "a.md")

    def test_avancar_sem_eleitoral_falha(self):
        dossie.marcar("caso", "triagem")
        dossie.responder("caso", "tamanho", "E2")
        with self.assertRaises(dossie.ErroDossie):
            dossie.marcar("caso", "levantamento")
        rc, _ = self.run_main("marcar", "caso", "levantamento")
        self.assertEqual(rc, 1)

    def test_avancar_com_respostas(self):
        self.responder_tudo()
        self.assertTrue(dossie.marcar("caso", "levantamento"))

    def test_valor_invalido(self):
        with self.assertRaises(dossie.ErroDossie):
            dossie.responder("caso", "tamanho", "E9")
        with self.assertRaises(dossie.ErroDossie):
            dossie.responder("caso", "eleitoral", "talvez")

    def test_passo_desconhecido(self):
        with self.assertRaises(dossie.ErroDossie):
            dossie.marcar("caso", "inventado")

    def test_fechar_sem_aprendizado_falha(self):
        with self.assertRaises(dossie.ErroDossie):
            dossie.fechar("caso")
        dossie.responder("caso", "aprendizado", "nada a propor")
        dossie.fechar("caso")
        self.assertIsNotNone(dossie.carregar("caso")["fechado"])

    def test_fechar_com_aprendizado_proposto(self):
        dossie.responder("caso", "aprendizado", "proposto")
        dossie.fechar("caso")

    def test_estado_truncado_nao_e_sobrescrito(self):
        arq = dados.arquivo_no_dossie("caso", "estado.json")
        arq.write_text('{"slug": "caso", "passos": {', encoding="utf-8")
        with self.assertRaises(dossie.ErroDossie):
            dossie.carregar("caso")
        rc, _ = self.run_main("marcar", "caso", "triagem")
        self.assertEqual(rc, 1)
        self.assertEqual(arq.read_text(encoding="utf-8"), '{"slug": "caso", "passos": {')

    def test_estrutura_invalida(self):
        arq = dados.arquivo_no_dossie("caso", "estado.json")
        arq.write_text("[]", encoding="utf-8")
        with self.assertRaises(dossie.ErroDossie):
            dossie.carregar("caso")

    def test_sem_sobra_de_temporario(self):
        dossie.marcar("caso", "triagem")
        nomes = [p.name for p in dados.pasta_dossie("caso").iterdir()]
        self.assertEqual(nomes, ["estado.json"])

    def test_uso_errado(self):
        self.assertEqual(self.run_main()[0], 2)
        self.assertEqual(self.run_main("marcar", "caso")[0], 2)
        self.assertEqual(self.run_main("marcar", "caso", "triagem", "--evidencia")[0], 2)
        self.assertEqual(self.run_main("marcar", "caso", "triagem", "--pesquisa", "x")[0], 2)
        self.assertEqual(self.run_main("marcar", "caso", "entrega", "--pesquisa", "x")[0], 2)
        self.assertEqual(self.run_main("marcar", "caso", "entrega", "--evidencia", "a", "--outra", "x")[0], 2)
        self.assertEqual(dossie.carregar("caso")["passos"], {})

    def test_entrega_exige_evidencia_depois_da_triagem(self):
        # ordem das recusas: triagem sem respostas vem antes da conferência da entrega
        with self.assertRaisesRegex(dossie.ErroDossie, "triagem"):
            dossie.marcar("caso", "entrega")
        self.responder_tudo()
        with self.assertRaisesRegex(dossie.ErroDossie, "--evidencia"):
            dossie.marcar("caso", "entrega")
        with self.assertRaisesRegex(dossie.ErroDossie, "não existe"):
            dossie.marcar("caso", "entrega", str(Path(self.tmp.name) / "nao-existe.md"))
        self.assertEqual(dossie.carregar("caso")["passos"], {})


if __name__ == "__main__":
    unittest.main()
