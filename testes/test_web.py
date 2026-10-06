"""
Testes da interface web (main.py) com o cliente de testes do Flask.

A captura é SIMULADA com empresas fictícias, apenas para testar as rotas
offline. O teste com dados reais é feito à parte (ver README).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main
from captura import ErroCaptura
from contrato_dados import CONTAS_OBRIGATORIAS
from setores import SETOR_DESTAQUE

CONTAS = {
    "ativo_circulante": 500.0, "passivo_circulante": 300.0, "estoque": None,
    "contas_a_receber": 90.0, "fornecedores": 80.0, "ativo_total": 1500.0,
    "passivo_total": 900.0, "patrimonio_liquido": 600.0, "receita_liquida": 2000.0,
    "cmv": 1200.0, "lucro_liquido": 150.0,
}


def empresa_falsa(ticker, nome, setor):
    return {"ticker": ticker, "nome": nome, "setor": setor,
            "anos": {2023: dict(CONTAS), 2024: {**CONTAS, "lucro_liquido": 200.0}}}


def concorrentes_falsos(setor, ticker_excluido):
    return {"empresas": [empresa_falsa("MOVI3.SA", "Movida", setor),
                         empresa_falsa("VAMO3.SA", "Vamos", setor)],
            "falhas": [("SIMH3.SA", "Falha simulada na fonte")]}


class TestWeb(unittest.TestCase):
    def setUp(self):
        main.app.config["TESTING"] = True
        self.cliente = main.app.test_client()
        main.ANALISES.clear()
        self.pasta = tempfile.mkdtemp()
        patchers = [
            mock.patch.object(main, "capturar_empresa", side_effect=empresa_falsa),
            mock.patch.object(main, "capturar_concorrentes", side_effect=concorrentes_falsos),
            mock.patch.object(main, "PASTA_RELATORIOS", Path(self.pasta) / "relatorios"),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def analisar(self, ticker="RENT3.SA"):
        return self.cliente.post("/analisar", data={"ticker": ticker})

    # ---- tela inicial ----
    def test_inicio_carrega_com_setores_empresas_e_localiza(self):
        resposta = self.cliente.get("/")
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        for setor in main.SETORES:
            self.assertIn(setor, html)
        self.assertIn("Localiza&amp;Co", html)
        self.assertIn("RENT3.SA", html)
        self.assertIn("Analisar empresa", html)
        self.assertIn("Fonte dos dados", html)
        self.assertIn(main.INTEGRANTES[0], html)
        # Localiza vem selecionada por padrão
        self.assertRegex(html, r'<option value="RENT3.SA"[^>]*selected')
        self.assertRegex(html, rf'<option value="{SETOR_DESTAQUE}" selected')

    def test_css_e_js_carregam(self):
        html = self.cliente.get("/").get_data(as_text=True)
        self.assertIn("/static/css/style.css", html)
        self.assertIn("/static/js/app.js", html)
        for caminho in ("/static/css/style.css", "/static/js/app.js"):
            resposta = self.cliente.get(caminho)
            self.assertEqual(resposta.status_code, 200, caminho)
            resposta.close()

    def test_interface_nao_usa_recursos_externos(self):
        for pagina in (self.cliente.get("/"), self.analisar()):
            html = pagina.get_data(as_text=True)
            self.assertNotRegex(html, r'(src|href)\s*=\s*"https?://')

    # ---- resultado ----
    def test_resultado_completo(self):
        resposta = self.analisar()
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Localiza&amp;Co", html)
        self.assertIn("RENT3.SA", html)
        self.assertIn("Resumo da análise", html)
        self.assertIn("Liquidez corrente", html)
        self.assertIn("ROE", html)
        self.assertIn("<th>2023</th>", html)
        self.assertEqual(html.count('src="data:image/png;base64,'), 4)
        self.assertIn("Interpretação", html)
        self.assertIn("Metodologia e limitações", html)
        self.assertIn("Gerar relatório", html)
        self.assertIn("Última análise", html)

    def test_dado_ausente_nao_vira_zero(self):
        html = self.analisar().get_data(as_text=True)
        self.assertIn("Não disponível", html)               # estoque None -> liquidez seca
        self.assertIn('<td class="indisponivel">Não disponível</td>', html)
        self.assertNotRegex(html, r"Liquidez seca</td>(<td[^>]*>0\.00</td>)+")

    def test_comparacao_setorial_lista_pares_e_falhas(self):
        html = self.analisar().get_data(as_text=True)
        self.assertIn("Comparação com empresas do setor", html)
        self.assertIn("Movida (MOVI3.SA)", html)
        self.assertIn("Quantidade de pares: <strong>2</strong>", html)
        self.assertIn("SIMH3.SA: Falha simulada na fonte", html)   # falha visível na página

    def test_aviso_de_poucos_pares(self):
        poucos = {"empresas": [empresa_falsa("MOVI3.SA", "Movida", "x")], "falhas": []}
        with mock.patch.object(main, "capturar_concorrentes", return_value=poucos):
            html = self.analisar().get_data(as_text=True)
        self.assertIn("A quantidade de empresas comparáveis é pequena", html)

    def test_sem_nenhum_par_a_analise_continua(self):
        vazio = {"empresas": [], "falhas": [("MOVI3.SA", "x"), ("VAMO3.SA", "y")]}
        with mock.patch.object(main, "capturar_concorrentes", return_value=vazio):
            resposta = self.analisar()
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Nenhuma empresa comparável foi capturada",
                      resposta.get_data(as_text=True))

    # ---- erros ----
    def test_erro_de_captura_aparece_na_interface(self):
        with mock.patch.object(main, "capturar_empresa",
                               side_effect=ErroCaptura("A fonte não devolveu demonstrações")):
            resposta = self.analisar()
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 502)
        self.assertIn("Não foi possível obter os dados da empresa", html)
        self.assertIn("A fonte não devolveu demonstrações", html)
        self.assertNotIn("Traceback", html)

    def test_ticker_invalido(self):
        resposta = self.analisar("XXXX9.SA")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Empresa inválida", resposta.get_data(as_text=True))

    def test_erro_inesperado_nao_finge_sucesso(self):
        with mock.patch.object(main, "capturar_empresa", side_effect=RuntimeError("boom")), \
                self.assertLogs(main.app.logger, level="ERROR"):
            resposta = self.analisar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("erro inesperado", resposta.get_data(as_text=True))

    # ---- relatório ----
    def id_da_analise(self):
        html = self.analisar().get_data(as_text=True)
        return html.split("/relatorio/")[1].split('"')[0]

    def test_gerar_relatorio_baixa_html_autocontido(self):
        resposta = self.cliente.post(f"/relatorio/{self.id_da_analise()}")
        self.addCleanup(resposta.close)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("attachment", resposta.headers["Content-Disposition"])
        self.assertIn("relatorio_RENT3_", resposta.headers["Content-Disposition"])
        conteudo = resposta.get_data(as_text=True)
        self.assertIn("<style>", conteudo)
        self.assertEqual(conteudo.count('src="data:image/png;base64,'), 4)
        self.assertNotIn("<script", conteudo)
        arquivos = list((Path(self.pasta) / "relatorios").glob("relatorio_RENT3_*.html"))
        self.assertEqual(len(arquivos), 1)       # também gravado em relatorios/

    def test_relatorio_de_analise_inexistente(self):
        resposta = self.cliente.post("/relatorio/naoexiste")
        self.assertEqual(resposta.status_code, 404)
        self.assertIn("Análise não encontrada", resposta.get_data(as_text=True))

    def test_memoria_guarda_no_maximo_n_analises(self):
        for _ in range(main.MAX_ANALISES_EM_MEMORIA + 3):
            self.analisar()
        self.assertEqual(len(main.ANALISES), main.MAX_ANALISES_EM_MEMORIA)

    def test_cartoes_de_destaque(self):
        html = self.analisar().get_data(as_text=True)
        self.assertEqual(html.count('class="kpi"'), 4)
        self.assertIn("Liquidez corrente", html)
        # estoque ausente não afeta os 4 destaques; ROE existe nos dados falsos
        self.assertIn("relativamente estável", html)

    def test_destaque_indisponivel_nao_vira_zero(self):
        indicadores = {2023: {n: None for n in main.NOMES_INDICADORES},
                       2024: {n: None for n in main.NOMES_INDICADORES}}
        for cartao in main.montar_destaques(indicadores):
            self.assertEqual(cartao["valor"], "Não disponível")
            self.assertTrue(cartao["indisponivel"])

    def test_nomes_da_dupla_aparecem(self):
        html = self.cliente.get("/").get_data(as_text=True)
        self.assertIn("Leonardo Chiari", html)
        self.assertIn("Rodrigo Prates", html)

    def test_abas_dos_graficos_tem_familia(self):
        html = self.analisar().get_data(as_text=True)
        for familia in ("Liquidez", "Endividamento", "Rentabilidade", "Atividade"):
            self.assertIn(f'data-familia="{familia}"', html)

    def test_metodos_http_corretos(self):
        self.assertEqual(self.cliente.get("/analisar").status_code, 405)


if __name__ == "__main__":
    unittest.main()
