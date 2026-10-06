"""
Testes de interpretacao.py. Rodam offline, com dados fictícios
(usados somente para testar as funções).
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import interpretacao as itp
from contrato_dados import CONTAS_OBRIGATORIAS
from indicadores import calcular_indicadores
from referencia_setorial import MIN_PARES


def empresa_ficticia(anos, setor="Teste"):
    return {"ticker": "T3.SA", "nome": "Teste", "setor": setor,
            "anos": {ano: {conta: contas.get(conta) for conta in CONTAS_OBRIGATORIAS}
                     for ano, contas in anos.items()}}


def liquidez(ativo, passivo, **extra):
    return {"ativo_circulante": ativo, "passivo_circulante": passivo, **extra}


def media(ano, nome, valor, n):
    return {ano: {nome: {"media": valor, "n": n}}}


def texto_do_indicador(empresa, nome, media_setorial=None):
    indicadores = calcular_indicadores(empresa)
    return itp.interpretar_indicador(nome, empresa, indicadores, media_setorial or {})


class TestClassificacoes(unittest.TestCase):
    def test_aumento_reducao_estabilidade(self):
        self.assertEqual(itp.classificar_variacao(1.0, 1.5), "aumentou")
        self.assertEqual(itp.classificar_variacao(1.0, 0.5), "diminuiu")
        self.assertEqual(itp.classificar_variacao(1.0, 1.05), "estavel")
        self.assertEqual(itp.classificar_variacao(1.0, 0.95), "estavel")

    def test_none_nao_e_comparado(self):
        self.assertIsNone(itp.classificar_variacao(None, 1.0))
        self.assertIsNone(itp.classificar_variacao(1.0, None))
        self.assertIsNone(itp.comparar_com_media(None, 1.0))
        self.assertIsNone(itp.comparar_com_media(1.0, None))

    def test_acima_abaixo_em_linha(self):
        self.assertEqual(itp.comparar_com_media(1.5, 1.0), "acima")
        self.assertEqual(itp.comparar_com_media(0.5, 1.0), "abaixo")
        self.assertEqual(itp.comparar_com_media(1.09, 1.0), "em linha")

    def test_base_zero_nao_quebra(self):
        self.assertEqual(itp.classificar_variacao(0.0, 0.0), "estavel")
        self.assertEqual(itp.classificar_variacao(0.0, 0.2), "aumentou")

    def test_sentido_segue_tendencia_geral(self):
        self.assertEqual(itp.classificar_sentido("liquidez_corrente", "aumentou"), "favoravel")
        self.assertEqual(itp.classificar_sentido("endividamento_geral", "aumentou"), "nao_favoravel")
        self.assertEqual(itp.classificar_sentido("pmr", "diminuiu"), "favoravel")
        self.assertIsNone(itp.classificar_sentido("pmp", "aumentou"))     # "depende"
        self.assertIsNone(itp.classificar_sentido("roa", "estavel"))

    def test_todo_indicador_tem_tendencia_nome_e_familia(self):
        em_familias = [n for nomes in itp.FAMILIAS.values() for n in nomes]
        self.assertEqual(sorted(em_familias), sorted(itp.TENDENCIA_GERAL))
        self.assertEqual(sorted(itp.NOMES_INDICADORES), sorted(itp.TENDENCIA_GERAL))


class TestTextoDoIndicador(unittest.TestCase):
    def test_evolucao_com_aumento(self):
        empresa = empresa_ficticia({2023: liquidez(100, 100), 2024: liquidez(200, 100)})
        texto = texto_do_indicador(empresa, "liquidez_corrente")
        self.assertIn("aumentou", texto)
        self.assertIn("favorável", texto)

    def test_reducao(self):
        empresa = empresa_ficticia({2023: liquidez(200, 100), 2024: liquidez(100, 100)})
        self.assertIn("diminuiu", texto_do_indicador(empresa, "liquidez_corrente"))

    def test_estabilidade(self):
        empresa = empresa_ficticia({2023: liquidez(100, 100), 2024: liquidez(103, 100)})
        self.assertIn("relativamente estável", texto_do_indicador(empresa, "liquidez_corrente"))

    def test_indicador_none(self):
        empresa = empresa_ficticia({2023: liquidez(100, 100), 2024: liquidez(None, 100)})
        texto = texto_do_indicador(empresa, "liquidez_corrente")
        self.assertIn("Não disponível", texto)
        self.assertNotIn("aumentou", texto)
        self.assertNotIn("diminuiu", texto)

    def test_sem_ano_anterior(self):
        empresa = empresa_ficticia({2024: liquidez(200, 100)})
        texto = texto_do_indicador(empresa, "liquidez_corrente")
        self.assertIn("apenas um ano", texto)
        self.assertNotIn("aumentou", texto)

    def test_ano_anterior_sem_dado(self):
        empresa = empresa_ficticia({2023: liquidez(None, 100), 2024: liquidez(200, 100)})
        self.assertIn("Sem dado em 2023", texto_do_indicador(empresa, "liquidez_corrente"))

    def test_pmp_nao_e_chamado_de_melhor_nem_pior(self):
        base = {"fornecedores": 10, "cmv": 100}
        empresa = empresa_ficticia({2023: base, 2024: {**base, "fornecedores": 30}})
        texto = texto_do_indicador(empresa, "pmp")
        self.assertIn("aumentou", texto)
        self.assertNotIn("favorável", texto)

    def test_indicador_de_estoque_ausente_tem_aviso_de_pouca_representatividade(self):
        empresa = empresa_ficticia({2024: liquidez(200, 100)})
        self.assertIn("pouco representativo", texto_do_indicador(empresa, "pme"))


class TestSetor(unittest.TestCase):
    def setUp(self):
        self.empresa = empresa_ficticia({2024: liquidez(200, 100)})   # 2,0

    def test_acima_da_media(self):
        t = texto_do_indicador(self.empresa, "liquidez_corrente",
                               media(2024, "liquidez_corrente", 1.0, MIN_PARES))
        self.assertIn("acima da média", t)
        self.assertIn(f"n = {MIN_PARES}", t)

    def test_abaixo_da_media(self):
        t = texto_do_indicador(self.empresa, "liquidez_corrente",
                               media(2024, "liquidez_corrente", 4.0, 3))
        self.assertIn("abaixo da média", t)

    def test_em_linha(self):
        t = texto_do_indicador(self.empresa, "liquidez_corrente",
                               media(2024, "liquidez_corrente", 2.1, 3))
        self.assertIn("aproximadamente em linha", t)

    def test_poucos_pares_nao_classifica(self):
        t = texto_do_indicador(self.empresa, "liquidez_corrente",
                               media(2024, "liquidez_corrente", 1.0, MIN_PARES - 1))
        self.assertIn("limitada", t)
        self.assertNotIn("acima da média", t)
        self.assertNotIn("abaixo da média", t)

    def test_sem_referencia(self):
        t = texto_do_indicador(self.empresa, "liquidez_corrente", {})
        self.assertIn("Sem referência setorial", t)


class TestPatrimonioNegativo(unittest.TestCase):
    def empresa_pl_negativo(self):
        contas = {"patrimonio_liquido": -100, "passivo_total": 500, "ativo_total": 400,
                  "lucro_liquido": -50, "receita_liquida": 1000}
        return empresa_ficticia({2023: contas, 2024: contas})

    def test_roe_e_explicado_e_nao_classificado(self):
        t = texto_do_indicador(self.empresa_pl_negativo(), "roe")
        self.assertIn("patrimônio líquido", t)
        self.assertIn("zero ou negativo", t)
        self.assertNotIn("aumentou", t)

    def test_divida_sobre_patrimonio_nao_e_classificada(self):
        t = texto_do_indicador(self.empresa_pl_negativo(), "divida_sobre_patrimonio",
                               media(2024, "divida_sobre_patrimonio", 2.0, 3))
        self.assertIn("zero ou negativo", t)
        self.assertNotIn("acima da média", t)
        self.assertNotIn("abaixo da média", t)


class TestInterpretacaoCompleta(unittest.TestCase):
    def test_estrutura_e_ausencia_de_recomendacao(self):
        empresa = empresa_ficticia({2023: liquidez(100, 100), 2024: liquidez(200, 100)})
        resultado = itp.gerar_interpretacao(empresa, calcular_indicadores(empresa), {})
        self.assertEqual(list(resultado["familias"]), ["Liquidez", "Endividamento",
                                                       "Rentabilidade", "Atividade"])
        self.assertEqual(len(resultado["familias"]["Atividade"]["itens"]), 5)
        todo = " ".join(resultado["resumo"]).lower()
        self.assertIn("não constitui recomendação", todo)
        self.assertNotRegex(todo, r"\b(compre|venda|mantenha)\b")

    def test_nota_de_locadora_so_para_o_setor_da_localiza(self):
        locadora = empresa_ficticia({2024: liquidez(200, 100)}, setor=itp.SETOR_DESTAQUE)
        outra = empresa_ficticia({2024: liquidez(200, 100)}, setor="Varejo")
        n_locadora = itp.gerar_interpretacao(locadora, calcular_indicadores(locadora), {})
        n_outra = itp.gerar_interpretacao(outra, calcular_indicadores(outra), {})
        self.assertTrue(any("locadoras" in n for n in n_locadora["familias"]["Atividade"]["notas"]))
        self.assertFalse(any("locadoras" in n for n in n_outra["familias"]["Atividade"]["notas"]))

    def test_sem_pares_resumo_informa(self):
        empresa = empresa_ficticia({2023: liquidez(100, 100), 2024: liquidez(200, 100)})
        resumo = " ".join(itp.gerar_resumo(empresa, calcular_indicadores(empresa), {}))
        self.assertIn("Não houve pares suficientes", resumo)

    def test_nenhum_emoji(self):
        empresa = empresa_ficticia({2023: liquidez(100, 100), 2024: liquidez(200, 100)})
        r = itp.gerar_interpretacao(empresa, calcular_indicadores(empresa), {})
        todo = " ".join(r["resumo"] + [i for f in r["familias"].values() for i in f["itens"] + f["notas"]])
        self.assertIsNone(re.search("[\U0001F300-\U0001FAFF☀-➿]", todo))


if __name__ == "__main__":
    unittest.main()
