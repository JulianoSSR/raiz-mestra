import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "scripts"))
import validar_skill  # noqa: E402

FIX = AQUI / "fixtures"


class TestValidarSkill(unittest.TestCase):
    def skill(self, nome, texto):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / nome
        p.mkdir()
        (p / "SKILL.md").write_text(texto, encoding="utf-8")
        return p

    def test_boa_aprova(self):
        self.assertEqual(validar_skill.validar(FIX / "boas" / "skill-boa"), [])

    def test_campo_extra_reprova(self):
        erros = validar_skill.validar(FIX / "ruins" / "skill-campo-extra")
        self.assertTrue(any("autor" in e for e in erros))

    def test_nome_diferente_da_pasta(self):
        erros = validar_skill.validar(FIX / "ruins" / "outro-nome")
        self.assertTrue(any("difere" in e for e in erros))

    def test_501_linhas(self):
        cab = "---\nname: grande\ndescription: x\n---\n"
        p = self.skill("grande", cab + "linha\n" * 497)  # 4 + 497 = 501
        self.assertEqual(len((p / "SKILL.md").read_text().splitlines()), 501)
        self.assertTrue(any("501 linhas" in e for e in validar_skill.validar(p)))

    def test_499_linhas_passa(self):
        cab = "---\nname: grande\ndescription: x\n---\n"
        p = self.skill("grande", cab + "l\n" * 495)
        self.assertEqual(validar_skill.validar(p), [])

    def test_sem_skill_md(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(validar_skill.validar(d))

    def test_sem_frontmatter(self):
        p = self.skill("x", "# nada\n")
        self.assertTrue(validar_skill.validar(p))

    def test_nome_maiusculo(self):
        p = self.skill("Maius", "---\nname: Maius\ndescription: x\n---\n")
        self.assertTrue(validar_skill.validar(p))

    def test_description_longa_e_compat_longa(self):
        p = self.skill("a", "---\nname: a\ndescription: %s\ncompatibility: %s\n---\n" % ("d" * 1025, "c" * 501))
        erros = validar_skill.validar(p)
        self.assertTrue(any("description" in e for e in erros))
        self.assertTrue(any("compatibility" in e for e in erros))

    def test_tokens_estimados(self):
        corpo = ("x" * 99 + "\n") * 110  # ~11.000 caracteres, ~3.143 tokens
        p = self.skill("a", "---\nname: a\ndescription: x\n---\n" + corpo)
        self.assertTrue(any("estimativa" in e for e in validar_skill.validar(p)))

    def test_main_codigos(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(validar_skill.main([str(FIX / "boas" / "skill-boa")]), 0)
            self.assertEqual(validar_skill.main([str(FIX / "ruins" / "outro-nome")]), 1)
            self.assertEqual(validar_skill.main([]), 2)


if __name__ == "__main__":
    unittest.main()
