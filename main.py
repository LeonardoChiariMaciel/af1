"""
main.py

PROGRAMA PRINCIPAL: interface web LOCAL (Flask) da aplicação.

Trabalho 1 de Administração Financeira (CAD 167), UFMG.
Tema: análise de demonstrações financeiras.

Papel no fluxo: sobe um servidor Flask na própria máquina (nada vai para a
internet) e liga a tela no navegador aos módulos de análise:

    navegador (templates/ + static/)
      -> main.py (rotas Flask)
      -> captura.py (yfinance) -> indicadores.py
      -> referencia_setorial.py (concorrentes) -> interpretacao.py
      -> relatorio.py (blocos HTML e arquivo do relatório)

Rotas:
    GET  /                      tela inicial: escolha de setor e empresa
    POST /analisar              executa a análise e mostra os resultados
    POST /relatorio/<id>        gera e baixa o relatório HTML da análise

Uso:
    python main.py              (abre http://127.0.0.1:5000 no navegador)
    python main.py --nao-abrir  (apenas inicia o servidor)
"""

import argparse
import sys
import threading
import webbrowser
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Flask, render_template, request, send_file

from captura import ErroCaptura, capturar_empresa
from indicadores import calcular_indicadores
from interpretacao import gerar_interpretacao
from referencia_setorial import calcular_media_setorial, capturar_concorrentes
from interpretacao import NOMES_INDICADORES, classificar_variacao
from relatorio import (DISCIPLINA, FONTE_DOS_DADOS, gerar_relatorio, montar_secoes,
                       texto_indicador)
from setores import SETOR_DESTAQUE, SETORES, buscar_empresa_por_ticker

# Nomes da dupla: aparecem na tela inicial, no rodapé e no relatório. Basta editar aqui.
INTEGRANTES = [
    "Leonardo Chiari",
    "Rodrigo Prates",
]

# Endereço local. 127.0.0.1 significa "esta máquina": só ela acessa o servidor.
HOST = "127.0.0.1"
PORTA = 5000

# Pasta onde os relatórios são gravados (ao lado deste arquivo)
PASTA_RELATORIOS = Path(__file__).resolve().parent / "relatorios"

# Quantas análises ficam guardadas na memória do servidor, para o botão
# "Gerar relatório" não precisar capturar tudo de novo. As mais antigas saem.
MAX_ANALISES_EM_MEMORIA = 10

app = Flask(__name__)

# {id: dicionário da análise}. Só guarda resultados de análises feitas nesta
# execução (dados capturados agora); não é cache nem plano B para a captura.
ANALISES = OrderedDict()


# ----------------------------------------------------------------------
# Lógica da análise (sem Flask): reaproveita os módulos existentes
# ----------------------------------------------------------------------

def executar_analise(ticker):
    """
    Executa o fluxo completo para um ticker da lista de setores.

    Devolve um dicionário com tudo o que a tela e o relatório precisam.
    Levanta ErroCaptura se a empresa principal não puder ser capturada
    (falha de concorrente NÃO levanta erro: fica registrada em "falhas").
    """
    encontrada = buscar_empresa_por_ticker(ticker)
    if encontrada is None:
        raise ValueError(f"Ticker fora da lista de empresas: {ticker}")
    ticker, nome, setor = encontrada

    empresa = capturar_empresa(ticker, nome, setor)
    indicadores = calcular_indicadores(empresa)

    concorrentes = capturar_concorrentes(setor, ticker)
    media_setorial = calcular_media_setorial(concorrentes["empresas"])
    interpretacao = gerar_interpretacao(empresa, indicadores, media_setorial)

    return {
        "empresa": empresa,
        "indicadores": indicadores,
        "media_setorial": media_setorial,
        "interpretacao": interpretacao,
        "falhas": concorrentes["falhas"],
        "pares": concorrentes["empresas"],
        "momento": datetime.now().strftime("%d/%m/%Y às %H:%M"),
    }


# Indicadores mostrados em destaque no topo dos resultados (um de cada família
# principal). São apenas uma vitrine: os 12 indicadores aparecem na tabela.
INDICADORES_EM_DESTAQUE = ("liquidez_corrente", "endividamento_geral",
                           "margem_liquida", "roe")

_DESCRICAO_VARIACAO = {"aumentou": "aumentou", "diminuiu": "diminuiu",
                       "estavel": "relativamente estável"}


def montar_destaques(indicadores):
    """
    Monta os cartões de destaque: valor do último ano e, quando possível, o
    movimento em relação ao ano anterior. A descrição é neutra (aumentou,
    diminuiu, estável): sem cor de "bom" ou "ruim", pois a leitura depende
    do contexto da empresa. Indicador None aparece como "Não disponível".
    """
    anos = sorted(indicadores)
    ultimo = anos[-1]
    anterior = anos[-2] if len(anos) >= 2 else None
    cartoes = []
    for nome in INDICADORES_EM_DESTAQUE:
        valor = indicadores[ultimo][nome]
        nota = f"Em {ultimo}"
        if valor is not None and anterior is not None:
            antigo = indicadores[anterior][nome]
            movimento = classificar_variacao(antigo, valor)
            if movimento is not None:
                nota += (f" | {_DESCRICAO_VARIACAO[movimento]} frente a {anterior} "
                         f"({texto_indicador(nome, antigo)})")
        cartoes.append({"rotulo": NOMES_INDICADORES[nome],
                        "valor": texto_indicador(nome, valor),
                        "indisponivel": valor is None, "nota": nota})
    return cartoes


def guardar_analise(analise):
    """Guarda a análise na memória e devolve o identificador dela."""
    id_analise = uuid4().hex
    ANALISES[id_analise] = analise
    while len(ANALISES) > MAX_ANALISES_EM_MEMORIA:
        ANALISES.popitem(last=False)   # remove a mais antiga
    return id_analise


# ----------------------------------------------------------------------
# Rotas
# ----------------------------------------------------------------------

def mostrar_inicio(status=200, erro=None, ticker_escolhido=None):
    """Renderiza a tela inicial (opcionalmente com uma mensagem de erro)."""
    escolhida = buscar_empresa_por_ticker(ticker_escolhido or "")
    ticker_padrao = escolhida[0] if escolhida else SETORES[SETOR_DESTAQUE][0][0]
    setor_padrao = escolhida[2] if escolhida else SETOR_DESTAQUE
    return render_template("index.html", setores=SETORES, erro=erro,
                           ticker_escolhido=ticker_padrao, setor_escolhido=setor_padrao,
                           integrantes=INTEGRANTES, disciplina=DISCIPLINA,
                           fonte=FONTE_DOS_DADOS), status


@app.get("/")
def inicio():
    """Tela inicial: apresentação e seleção de setor e empresa."""
    return mostrar_inicio()


@app.post("/analisar")
def analisar():
    """
    Executa a análise da empresa escolhida e mostra os resultados.

    Erros esperados (ticker inválido, falha da fonte) voltam para a tela
    inicial com uma mensagem em português, e não como página de erro técnica.
    """
    ticker = request.form.get("ticker", "").strip()
    try:
        analise = executar_analise(ticker)
    except ValueError:
        return mostrar_inicio(400, {
            "titulo": "Empresa inválida.",
            "linhas": ["Escolha uma empresa da lista e tente novamente."]})
    except ErroCaptura as erro:
        return mostrar_inicio(502, {
            "titulo": "Não foi possível obter os dados da empresa.",
            "linhas": [str(erro),
                       "Verifique sua conexão com a internet e tente novamente."]},
            ticker_escolhido=ticker)
    except Exception as erro:   # erro inesperado: não finge sucesso
        app.logger.exception("Erro inesperado na análise de %s", ticker)
        return mostrar_inicio(500, {
            "titulo": "Ocorreu um erro inesperado durante a análise.",
            "linhas": [f"{type(erro).__name__}: {erro}",
                       "Nenhum resultado foi gerado. Tente novamente."]},
            ticker_escolhido=ticker)

    empresa = analise["empresa"]
    secoes = montar_secoes(empresa, analise["indicadores"], analise["media_setorial"],
                           analise["interpretacao"], analise["falhas"], analise["pares"])
    return render_template("resultado.html", empresa=empresa, secoes=secoes,
                           kpis=montar_destaques(analise["indicadores"]),
                           anos=sorted(empresa["anos"]), momento=analise["momento"],
                           id_analise=guardar_analise(analise),
                           integrantes=INTEGRANTES, disciplina=DISCIPLINA,
                           fonte=FONTE_DOS_DADOS)


@app.post("/relatorio/<id_analise>")
def baixar_relatorio(id_analise):
    """
    Gera o relatório HTML da análise (relatorio.gerar_relatorio), grava em
    relatorios/ e entrega o arquivo para download.
    """
    analise = ANALISES.get(id_analise)
    if analise is None:
        return mostrar_inicio(404, {
            "titulo": "Análise não encontrada.",
            "linhas": ["Ela pode ter expirado. Execute a análise novamente."]})
    caminho = gerar_relatorio(analise["empresa"], analise["indicadores"],
                              analise["media_setorial"], analise["interpretacao"],
                              analise["falhas"], PASTA_RELATORIOS,
                              pares_utilizados=analise["pares"], integrantes=INTEGRANTES)
    return send_file(caminho, mimetype="text/html", as_attachment=True,
                     download_name=caminho.name)


# ----------------------------------------------------------------------
# Inicialização
# ----------------------------------------------------------------------

def main():
    """Inicia o servidor local. Devolve o código de saída (0 = sucesso)."""
    parser = argparse.ArgumentParser(
        description="Interface web local para análise de demonstrações financeiras.")
    parser.add_argument("--nao-abrir", action="store_true",
                        help="inicia o servidor sem abrir o navegador")
    args = parser.parse_args()

    endereco = f"http://{HOST}:{PORTA}"
    print("Aplicação iniciada.")
    print(f"Acesse: {endereco}")
    print("Para encerrar, pressione Ctrl+C neste terminal.")
    if not args.nao_abrir:
        # Espera 1 segundo para o servidor já estar de pé quando o navegador abrir
        threading.Timer(1.0, webbrowser.open, args=[endereco]).start()

    try:
        app.run(host=HOST, port=PORTA, debug=False)
    except OSError as erro:
        print(f"\nNão foi possível iniciar o servidor em {endereco}: {erro}\n"
              f"Verifique se a porta {PORTA} já não está em uso por outro programa.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
