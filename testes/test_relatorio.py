"""
Testes de relatorio.py. Rodam offline, com dados fictícios
(usados somente para testar a geração do arquivo).
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import relatorio
from contrato_dados import CONTAS_OBRIGATORIAS
from indicadores import calcular_indicadores
from interpretacao import gerar_interpretacao
from referencia_setorial import calcular_media_setorial


def empresa_ficticia(ticker, nome, anos, setor="Teste"):
    return {"ticker": ticker, "nome": nome, "setor": setor,
            "anos": {ano: {conta: contas.get(conta) for conta in CONTAS_OBRIGATORIAS}
                     for ano, contas in anos.items()}}


# Conjunto de contas completo, para que quase todos os indicadores existam
CONTAS_COMPLETAS = {
    "ativo_circulante": 500.0, "passivo_circulante": 300.0, "estoque": 100.0,
    "contas_a_receber": 90.0, "fornecedores": 80.0, "ativo_total": 1500.0,
    "passivo_total": 900.0, "patrimonio_liquido": 600.0, "receita_liquida": 2000.0,
    "cmv": 1200.0, "lucro_liquido": 150.0,
}


class TestRelatorio(unittest.TestCase):
    def gerar(self, empresa, pares=(), falhas=(), nome_pasta="saida"):
        indicadores = calcular_indicadores(empresa)
        media = calcular_media_setorial(list(pares))
        interpretacao = gerar_interpretacao(empresa, indicadores, media)
        self.pasta = Path(tempfile.mkdtemp()) / nome_pasta   # ainda não existe
        caminho = relatorio.gerar_relatorio(
            empresa, indicadores, media, interpretacao, list(falhas), self.pasta,
            pares_utilizados=list(pares), integrantes=["Aluno Um", "Aluno Dois"])
        return caminho, caminho.read_text(encoding="utf-8")

    def setUp(self):
        self.empresa = empresa_ficticia("TST3.SA", "Empresa & Teste <S.A.>", {
            2023: dict(CONTAS_COMPLETAS),
            2024: {**CONTAS_COMPLETAS, "estoque": None, "lucro_liquido": 200.0},   # None em 2024
        })
        self.par1 = empresa_ficticia("P1.SA", "Par Um", {2024: dict(CONTAS_COMPLETAS)})
        self.par2 = empresa_ficticia("P2.SA", "Par Dois", {2024: dict(CONTAS_COMPLETAS)})

    def test_arquivo_criado_e_pasta_criada_automaticamente(self):
        caminho, conteudo = self.gerar(self.empresa, [self.par1, self.par2])
        self.assertTrue(caminho.exists())
        self.assertGreater(len(conteudo), 1000)
        self.assertEqual(caminho.name, f"relatorio_TST3_{__import__('datetime').date.today():%Y-%m-%d}.html")

    def test_conteudo_principal(self):
        _, html = self.gerar(self.empresa, [self.par1, self.par2],
                             falhas=[("XXX3.SA", "sem dados na fonte")])
        self.assertIn("Empresa &amp; Teste &lt;S.A.&gt;", html)      # escapado
        self.assertIn("TST3.SA", html)
        self.assertIn("<table>", html)
        self.assertIn("Liquidez corrente", html)
        self.assertIn("ROE", html)
        self.assertIn("Notas metodológicas", html)
        self.assertIn("365 dias", html)
        self.assertIn("Yahoo Finance", html)
        self.assertIn("Aluno Um", html)
        self.assertIn("Administração Financeira", html)
        self.assertIn("n = 2", html)                                  # tamanho da amostra
        self.assertIn("XXX3.SA", html)                                # falha listada
        self.assertIn("sem dados na fonte", html)
        self.assertIn("Par Um (P1.SA)", html)                         # par utilizado

    def test_none_aparece_como_nao_disponivel(self):
        _, html = self.gerar(self.empresa, [self.par1, self.par2])
        self.assertIn("Não disponível", html)   # liquidez seca de 2024 (estoque None)

    def test_quatro_graficos_embutidos(self):
        _, html = self.gerar(self.empresa, [self.par1, self.par2])
        self.assertEqual(html.count('src="data:image/png;base64,'), 4)

    def test_sem_dependencias_externas(self):
        _, html = self.gerar(self.empresa, [self.par1, self.par2])
        self.assertNotRegex(html, r'(src|href)\s*=\s*"https?://')
        self.assertNotIn("<script", html)
        self.assertNotIn("<link", html)
        self.assertIn("<style>", html)
        self.assertIn('<meta charset="utf-8">', html)

    def test_sem_pares_gera_relatorio_sem_comparacao(self):
        _, html = self.gerar(self.empresa, [])
        self.assertIn("Nenhuma empresa comparável foi capturada", html)
        self.assertNotIn("Média dos pares em", html)

    def test_nota_de_locadora_e_da_localiza_so_quando_se_aplicam(self):
        _, html = self.gerar(self.empresa, [])
        self.assertNotIn("Unidas", html)
        self.assertNotIn("locadoras de veículos", html)
        localiza = empresa_ficticia("RENT3.SA", "Localiza", {
            2023: dict(CONTAS_COMPLETAS), 2024: dict(CONTAS_COMPLETAS)},
            setor=relatorio.SETOR_DESTAQUE)
        _, html = self.gerar(localiza, [])
        self.assertIn("Unidas", html)
        self.assertIn("1º de julho de 2022", html)
        self.assertIn("locadoras de veículos", html)

    def test_sobrescreve_relatorio_do_mesmo_dia(self):
        caminho1, _ = self.gerar(self.empresa, [])
        indicadores = calcular_indicadores(self.empresa)
        interpretacao = gerar_interpretacao(self.empresa, indicadores, {})
        caminho2 = relatorio.gerar_relatorio(self.empresa, indicadores, {}, interpretacao,
                                             [], self.pasta)
        self.assertEqual(caminho1, caminho2)

    def test_nenhum_emoji(self):
        _, html = self.gerar(self.empresa, [self.par1, self.par2])
        self.assertIsNone(re.search("[\U0001F300-\U0001FAFF☀-➿]", html))


if __name__ == "__main__":
    unittest.main()
