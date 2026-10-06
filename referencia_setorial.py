"""
referencia_setorial.py

MÓDULO DE REFERÊNCIA SETORIAL.

Papel no fluxo: depois de analisar a empresa escolhida, captura os
concorrentes (lista fixa de setores.py) e calcula, para cada ano e cada
indicador, a MÉDIA dos pares. Essa média serve de régua para dizer se a
empresa está acima, abaixo ou em linha com o setor.

Entradas : setor e ticker da empresa analisada.
Saídas   : - capturar_concorrentes -> empresas capturadas + falhas (com motivo);
           - calcular_media_setorial -> {ano: {indicador: {"media", "n"}}}.

Os indicadores dos pares são calculados por calcular_indicadores()
(indicadores.py): nenhuma fórmula financeira é repetida aqui.
"""

from captura import capturar_empresa, ErroCaptura
from indicadores import calcular_indicadores
from setores import obter_concorrentes

# Número mínimo de pares com dado válido para a média ser usada em uma
# comparação setorial. Com menos que isso, a média é apenas informativa:
# a empresa é analisada pela própria evolução, sem ser classificada como
# acima ou abaixo do setor. É uma decisão metodológica do trabalho,
# não uma regra estatística universal.
MIN_PARES = 2


def capturar_concorrentes(setor, ticker_excluido):
    """
    Captura, um a um, os concorrentes do setor (menos a própria empresa).

    Se um concorrente falhar (ErroCaptura), o erro é registrado e os
    demais continuam: um par ruim não derruba a análise. Nada é ignorado
    em silêncio, porque cada falha aparece no terminal e no relatório.

    Devolve um dicionário:
        {
          "empresas": [empresa, ...],           # no formato do contrato
          "falhas":   [(ticker, motivo), ...],  # quem falhou e por quê
        }
    """
    empresas = []
    falhas = []
    for ticker, nome in obter_concorrentes(setor, ticker_excluido):
        print(f"Capturando {ticker}...")
        try:
            empresas.append(capturar_empresa(ticker, nome, setor))
        except ErroCaptura as erro:
            falhas.append((ticker, str(erro)))
            print(f"  Falhou: {erro}")
    return {"empresas": empresas, "falhas": falhas}


def calcular_media_setorial(empresas_pares):
    """
    Calcula a média setorial de cada indicador, ano a ano.

    empresas_pares: lista de empresas no formato do contrato (os pares).

    Para cada (ano, indicador): média aritmética simples dos valores dos
    pares que têm valor válido. Valores None são ignorados, não contam
    como zero e não entram em "n". Empresas podem ter anos diferentes:
    cada ano é combinado separadamente, sem presumir períodos iguais.

    Atenção: a média simples é sensível a valores extremos (um par muito
    alavancado, por exemplo, puxa a média) e, com poucos pares, representa
    apenas esses pares, não o setor inteiro.

    Devolve {ano: {indicador: {"media": valor ou None, "n": quantidade}}},
    com os anos em ordem crescente. Sem pares, devolve {}.
    """
    # Indicadores de cada par: [{ano: {indicador: valor}}, ...]
    indicadores_dos_pares = [calcular_indicadores(par) for par in empresas_pares]

    anos = sorted({ano for indicadores in indicadores_dos_pares for ano in indicadores})

    resultado = {}
    for ano in anos:
        resultado[ano] = {}
        # Nomes dos indicadores vistos neste ano em qualquer par
        nomes = {nome for indicadores in indicadores_dos_pares
                 for nome in indicadores.get(ano, {})}
        for nome in sorted(nomes):
            valores = [indicadores[ano][nome] for indicadores in indicadores_dos_pares
                       if ano in indicadores and indicadores[ano].get(nome) is not None]
            media = sum(valores) / len(valores) if valores else None
            resultado[ano][nome] = {"media": media, "n": len(valores)}
    return resultado


def referencia_suficiente(n):
    """True se há pares suficientes (n >= MIN_PARES) para uma comparação setorial."""
    return n >= MIN_PARES


# Teste com dados reais: python referencia_setorial.py [TICKER]
if __name__ == "__main__":
    import sys
    from indicadores import formatar_indicador
    from setores import buscar_empresa_por_ticker

    ticker_teste = sys.argv[1] if len(sys.argv) > 1 else "RENT3.SA"
    encontrada = buscar_empresa_por_ticker(ticker_teste)
    if encontrada is None:
        print("Ticker fora da lista de setores.py")
        sys.exit(1)

    capturados = capturar_concorrentes(encontrada[2], ticker_teste)
    print("Falhas:", capturados["falhas"])
    media = calcular_media_setorial(capturados["empresas"])
    for ano, indicadores in media.items():
        print(f"\nAno {ano}:")
        for nome, info in indicadores.items():
            print(f"  {nome}: {formatar_indicador(nome, info['media'])} (n = {info['n']})")
