"""
captura.py

MÓDULO DE CAPTURA (bloco A).

Baixa as demonstrações financeiras de uma empresa (balanço patrimonial e
DRE, anuais) pelo yfinance e as TRADUZ para o formato do contrato
(ver contrato_dados.py), que é o único formato que o módulo de
indicadores conhece.

Etapas:
  1. baixar_demonstracoes   -> usa a internet (yfinance)
  2. traduzir_para_contrato -> não usa internet (pode ser testada offline)
  3. validar_empresa        -> confere se o resultado respeita o contrato

Função principal: capturar_empresa(ticker, nome, setor)

Para testar com dados reais:
    python captura.py              (usa WEGE3.SA)
    python captura.py LREN3.SA     (usa o ticker informado)
"""

from contrato_dados import CONTAS_OBRIGATORIAS, validar_empresa


class ErroCaptura(Exception):
    """
    Erro esperado durante a captura (ticker inválido, sem internet etc.).

    A mensagem já é escrita para o usuário final, em português.
    """


# Para cada conta do contrato, os nomes que a fonte usa (em inglês).
# Confirmados no teste com WEGE3, LREN3 e TOTS3. Se o primeiro nome vier
# vazio (NaN) em um ano, tenta-se o seguinte.
MAPA_CONTAS_CANDIDATAS = {
    # Balanço patrimonial
    "ativo_circulante": ["Current Assets"],
    "passivo_circulante": ["Current Liabilities"],
    "estoque": ["Inventory"],
    "contas_a_receber": ["Accounts Receivable", "Receivables"],
    "fornecedores": ["Accounts Payable", "Payables"],
    "ativo_total": ["Total Assets"],
    "passivo_total": ["Total Liabilities Net Minority Interest"],
    "patrimonio_liquido": ["Stockholders Equity", "Common Stock Equity"],
    # DRE
    "receita_liquida": ["Total Revenue", "Operating Revenue"],
    "cmv": ["Cost Of Revenue"],
    "lucro_liquido": ["Net Income", "Net Income Common Stockholders"],
}

# Garante que este mapa e o contrato nunca fiquem desencontrados:
# se alguém adicionar uma conta ao contrato e esquecer aqui, falha logo.
assert set(MAPA_CONTAS_CANDIDATAS) == set(CONTAS_OBRIGATORIAS), (
    "MAPA_CONTAS_CANDIDATAS e CONTAS_OBRIGATORIAS estão diferentes"
)


def valor_ou_none(valor):
    """
    Converte um valor da fonte para o formato do contrato.

    A fonte marca dado vazio como NaN ("not a number"); o contrato usa
    None. Valores numéricos viram float comum do Python.
    """
    if valor is None:
        return None
    if valor != valor:   # NaN é o único valor diferente de si mesmo
        return None
    return float(valor)


def baixar_demonstracoes(ticker):
    """
    Baixa balanço e DRE anuais do ticker pelo yfinance.

    Devolve (balanco, dre), duas tabelas (DataFrames) em que cada linha
    é uma conta e cada coluna é um ano. Levanta ErroCaptura se algo falhar.
    """
    try:
        import yfinance as yf
    except ImportError as erro:
        raise ErroCaptura(
            "A biblioteca yfinance não está instalada. "
            "Instale com: pip install yfinance"
        ) from erro

    try:
        empresa = yf.Ticker(ticker)
        balanco = empresa.balance_sheet
        # Versões antigas do yfinance chamam a DRE de 'financials'
        dre = getattr(empresa, "income_stmt", None)
        if dre is None:
            dre = empresa.financials
    except Exception as erro:
        raise ErroCaptura(
            f"Não foi possível baixar os dados de '{ticker}'. "
            f"Verifique a conexão com a internet. (Detalhe: {erro})"
        ) from erro

    if balanco is None or balanco.empty or dre is None or dre.empty:
        raise ErroCaptura(
            f"A fonte não devolveu demonstrações para '{ticker}'. "
            "Verifique se o ticker está correto (exemplo: PETR4.SA), se há "
            "conexão com a internet e se antivírus ou proxy não está "
            "bloqueando o acesso ao Yahoo Finance."
        )
    return balanco, dre


def _colunas_por_ano(tabela):
    """Mapa {ano: coluna} de uma tabela da fonte (as colunas são datas)."""
    return {coluna.year: coluna for coluna in tabela.columns}


def _buscar_valor(conta, tabelas, colunas, ano):
    """
    Procura o valor de uma conta do contrato em um ano.

    Testa cada nome candidato, em cada tabela, e devolve o primeiro valor
    que não seja vazio. Se a linha não existe (ex.: estoque em empresa de
    software) ou está vazia em todos os candidatos, devolve None.
    """
    for nome_linha in MAPA_CONTAS_CANDIDATAS[conta]:
        for tabela, colunas_da_tabela in zip(tabelas, colunas):
            if nome_linha in tabela.index and ano in colunas_da_tabela:
                valor = valor_ou_none(tabela.loc[nome_linha, colunas_da_tabela[ano]])
                if valor is not None:
                    return valor
    return None


def traduzir_para_contrato(balanco, dre, ticker, nome, setor):
    """
    Traduz as tabelas da fonte para o dicionário do contrato.

    Não usa internet: recebe as tabelas prontas, o que permite testar
    com tabelas falsas.
    """
    tabelas = [balanco, dre]
    colunas = [_colunas_por_ano(tabela) for tabela in tabelas]

    # Todos os anos que aparecem em alguma das duas tabelas, do mais antigo
    # ao mais novo (a ordem facilita os gráficos de evolução)
    anos = sorted(set().union(*colunas))

    anos_traduzidos = {}
    for ano in anos:
        contas = {conta: _buscar_valor(conta, tabelas, colunas, ano)
                  for conta in CONTAS_OBRIGATORIAS}
        # Ano sem as contas-base (ativo total e receita líquida) não ajuda
        # ninguém: descarta. Na prática a fonte devolve uma coluna quase
        # vazia para o ano mais antigo (ex.: RENT3 2021 trazia só estoque = 0,
        # que passava pelo antigo filtro "todas as contas vazias").
        if contas["ativo_total"] is None and contas["receita_liquida"] is None:
            continue
        anos_traduzidos[ano] = contas

    if not anos_traduzidos:
        raise ErroCaptura(
            f"Os dados de '{ticker}' vieram sem nenhuma das contas esperadas."
        )

    return {
        "ticker": ticker,
        "nome": nome,
        "setor": setor,
        "anos": anos_traduzidos,
    }


def capturar_empresa(ticker, nome=None, setor=""):
    """
    Captura uma empresa completa, no formato do contrato.

    ticker: código na bolsa, com sufixo .SA para o Brasil (ex.: WEGE3.SA)
    nome:   nome para exibir no relatório (se omitido, usa o ticker)
    setor:  chave do setor na nossa tabela de setores

    Levanta ErroCaptura se não for possível capturar.
    """
    balanco, dre = baixar_demonstracoes(ticker)
    empresa = traduzir_para_contrato(balanco, dre, ticker, nome or ticker, setor)
    validar_empresa(empresa)   # confere o contrato antes de entregar
    return empresa


# Teste com dados reais: python captura.py [TICKER]
if __name__ == "__main__":
    import sys
    from indicadores import calcular_indicadores, formatar_indicador

    ticker_teste = sys.argv[1] if len(sys.argv) > 1 else "WEGE3.SA"

    try:
        dados = capturar_empresa(ticker_teste)
    except ErroCaptura as erro:
        print(f"Erro: {erro}")
        sys.exit(1)

    print(f"Dados capturados para {ticker_teste}: anos {sorted(dados['anos'])}")
    for ano, indicadores in calcular_indicadores(dados).items():
        print(f"\nAno {ano}:")
        for nome_indicador, valor in indicadores.items():
            print(f"  {nome_indicador}: {formatar_indicador(nome_indicador, valor)}")
