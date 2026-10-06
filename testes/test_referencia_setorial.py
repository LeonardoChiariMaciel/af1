"""
Testes de referencia_setorial.py. Rodam offline.

As empresas abaixo são FICTÍCIAS e servem só para testar as funções;
o programa final nunca usa dados assim no lugar da captura real.
"""

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import referencia_setorial as ref
from captura import ErroCaptura
from contrato_dados import CONTAS_OBRIGATORIAS


def empresa_ficticia(ticker, anos):
    """
    Monta uma empresa no formato do contrato.

    anos: {ano: {conta: valor}}. Contas não informadas ficam None.
    """
    return {
        "ticker": ticker, "nome": ticker, "setor": "Teste",
        "anos": {ano: {conta: contas.get(conta) for conta in CONTAS_OBRIGATORIAS}
                 for ano, contas in anos.items()},
    }


# Liquidez corrente = ativo_circulante / passivo_circulante
def com_liquidez(ativo, passivo):
    return {"ativo_circulante": ativo, "passivo_circulante": passivo}


class TestMediaSetorial(unittest.TestCase):
    def test_dois_pares(self):
        a = empresa_ficticia("A", {2024: com_liquidez(200, 100)})   # 2,0
        b = empresa_ficticia("B", {2024: com_liquidez(100, 100)})   # 1,0
        media = ref.calcular_media_setorial([a, b])
        self.assertAlmostEqual(media[2024]["liquidez_corrente"]["media"], 1.5)
        self.assertEqual(media[2024]["liquidez_corrente"]["n"], 2)

    def test_um_par(self):
        a = empresa_ficticia("A", {2024: com_liquidez(200, 100)})
        info = ref.calcular_media_setorial([a])[2024]["liquidez_corrente"]
        self.assertEqual(info["n"], 1)
        self.assertFalse(ref.referencia_suficiente(info["n"]))

    def test_nenhum_par(self):
        self.assertEqual(ref.calcular_media_setorial([]), {})

    def test_none_e_ignorado_e_nao_conta_em_n(self):
        a = empresa_ficticia("A", {2024: com_liquidez(200, 100)})
        b = empresa_ficticia("B", {2024: com_liquidez(None, 100)})   # None
        info = ref.calcular_media_setorial([a, b])[2024]["liquidez_corrente"]
        self.assertAlmostEqual(info["media"], 2.0)
        self.assertEqual(info["n"], 1)

    def test_indicador_sem_nenhum_valor_tem_media_none(self):
        a = empresa_ficticia("A", {2024: com_liquidez(200, 100)})
        b = empresa_ficticia("B", {2024: com_liquidez(100, 100)})
        info = ref.calcular_media_setorial([a, b])[2024]["roe"]
        self.assertIsNone(info["media"])
        self.assertEqual(info["n"], 0)

    def test_anos_diferentes_sao_combinados_por_ano(self):
        a = empresa_ficticia("A", {2023: com_liquidez(100, 100), 2024: com_liquidez(200, 100)})
        b = empresa_ficticia("B", {2024: com_liquidez(100, 100), 2025: com_liquidez(300, 100)})
        media = ref.calcular_media_setorial([a, b])
        self.assertEqual(list(media), [2023, 2024, 2025])      # ordem crescente
        self.assertEqual(media[2023]["liquidez_corrente"]["n"], 1)
        self.assertEqual(media[2024]["liquidez_corrente"]["n"], 2)
        self.assertAlmostEqual(media[2024]["liquidez_corrente"]["media"], 1.5)
        self.assertEqual(media[2025]["liquidez_corrente"]["n"], 1)

    def test_indicador_ausente_em_apenas_uma_empresa(self):
        # Só A informa estoque, então só A tem liquidez seca
        a = empresa_ficticia("A", {2024: {**com_liquidez(200, 100), "estoque": 50}})
        b = empresa_ficticia("B", {2024: com_liquidez(100, 100)})
        info = ref.calcular_media_setorial([a, b])[2024]["liquidez_seca"]
        self.assertAlmostEqual(info["media"], 1.5)
        self.assertEqual(info["n"], 1)

    def test_min_pares(self):
        self.assertTrue(ref.referencia_suficiente(ref.MIN_PARES))
        self.assertFalse(ref.referencia_suficiente(ref.MIN_PARES - 1))


class TestCapturarConcorrentes(unittest.TestCase):
    def test_falha_de_um_concorrente_nao_derruba_os_outros(self):
        def captura_falsa(ticker, nome, setor):
            if ticker == "VAMO3.SA":
                raise ErroCaptura("sem dados")
            return empresa_ficticia(ticker, {2024: com_liquidez(1, 1)})

        with mock.patch.object(ref, "capturar_empresa", side_effect=captura_falsa), \
                contextlib.redirect_stdout(io.StringIO()):
            resultado = ref.capturar_concorrentes("Locação de veículos e frotas", "RENT3.SA")

        tickers = [e["ticker"] for e in resultado["empresas"]]
        self.assertEqual(tickers, ["MOVI3.SA", "SIMH3.SA"])
        self.assertEqual(resultado["falhas"], [("VAMO3.SA", "sem dados")])
        self.assertNotIn("RENT3.SA", tickers)


if __name__ == "__main__":
    unittest.main()
