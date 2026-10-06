"""
Testes de setores.py (menu e concorrentes). Rodam offline.

Como rodar, na pasta do projeto:
    python -m unittest discover -s testes -v
"""

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import setores


def escolher_com_entradas(entradas):
    """Roda escolher_empresa() simulando o que o usuário digita."""
    with mock.patch("builtins.input", side_effect=entradas), \
            contextlib.redirect_stdout(io.StringIO()) as saida:
        resultado = setores.escolher_empresa()
    return resultado, saida.getvalue()


class TestMenu(unittest.TestCase):
    def test_opcao_valida(self):
        # Setor 1 (Locação), empresa 2 (Movida)
        resultado, _ = escolher_com_entradas(["1", "2"])
        self.assertEqual(resultado, ("MOVI3.SA", "Movida", setores.SETOR_DESTAQUE))

    def test_enter_escolhe_padrao_localiza(self):
        resultado, _ = escolher_com_entradas(["", ""])
        self.assertEqual(resultado[0], "RENT3.SA")

    def test_entrada_invalida_repete_pergunta(self):
        # "abc", "0" e "99" são inválidas; depois "2" (Varejo) e "1" (Renner)
        resultado, saida = escolher_com_entradas(["abc", "0", "99", "2", "1"])
        self.assertEqual(resultado[0], "LREN3.SA")
        self.assertEqual(saida.count("Opção inválida"), 3)

    def test_setor_destaque_e_o_primeiro(self):
        self.assertEqual(next(iter(setores.SETORES)), setores.SETOR_DESTAQUE)
        self.assertEqual(setores.SETORES[setores.SETOR_DESTAQUE][0][0], "RENT3.SA")


class TestConcorrentes(unittest.TestCase):
    def test_exclui_a_propria_empresa(self):
        concorrentes = setores.obter_concorrentes(setores.SETOR_DESTAQUE, "RENT3.SA")
        tickers = [ticker for ticker, _ in concorrentes]
        self.assertNotIn("RENT3.SA", tickers)
        self.assertEqual(tickers, ["MOVI3.SA", "VAMO3.SA", "SIMH3.SA"])

    def test_setor_inexistente_devolve_lista_vazia(self):
        self.assertEqual(setores.obter_concorrentes("Inexistente", "X"), [])

    def test_buscar_por_ticker(self):
        self.assertEqual(setores.buscar_empresa_por_ticker("rent3.sa"),
                         ("RENT3.SA", "Localiza&Co", setores.SETOR_DESTAQUE))
        self.assertIsNone(setores.buscar_empresa_por_ticker("XXXX3.SA"))


if __name__ == "__main__":
    unittest.main()
